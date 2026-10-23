from sqlalchemy import text
from sqlalchemy.orm import Session

EXPECTED_TABLES = {
    "tenants",
    "users",
    "data_sources",
    "model_settings",
    "tenant_settings",
    "sl_tables",
    "sl_columns",
    "sl_relationships",
    "kpis",
    "kpi_inputs",
    "kpi_rules",
    "conversations",
    "messages",
    "query_log",
    "datasets",
    "charts",
    "dashboards",
    "dashboard_items",
}

TENANT_OWNED = EXPECTED_TABLES - {"tenants"}

_TENANT_ID_INDEXED = """
select distinct c.relname
from pg_index i
join pg_class c on c.oid = i.indrelid
join pg_namespace n on n.oid = c.relnamespace
join pg_attribute a on a.attrelid = c.oid and a.attnum = any (i.indkey)
where n.nspname = 'public' and a.attname = 'tenant_id'
"""


def test_schema_contains_all_expected_tables(db: Session) -> None:
    names = set(
        db.execute(
            text(
                """
                select table_name
                from information_schema.tables
                where table_schema = 'public' and table_type = 'BASE TABLE'
                """
            )
        ).scalars()
    )
    assert names == EXPECTED_TABLES


def test_every_tenant_owned_table_has_tenant_id(db: Session) -> None:
    columns = set(
        db.execute(
            text(
                """
                select table_name
                from information_schema.columns
                where table_schema = 'public' and column_name = 'tenant_id'
                """
            )
        ).scalars()
    )
    assert columns == TENANT_OWNED

    # users.tenant_id is the one nullable exception: a Platform Admin belongs to no Tenant.
    not_null = set(
        db.execute(
            text(
                """
                select table_name
                from information_schema.columns
                where table_schema = 'public'
                  and column_name = 'tenant_id'
                  and is_nullable = 'NO'
                """
            )
        ).scalars()
    )
    assert not_null == TENANT_OWNED - {"users"}

    indexed = set(db.execute(text(_TENANT_ID_INDEXED)).scalars())
    assert indexed == TENANT_OWNED


def test_query_log_survives_conversation_deletion(db: Session) -> None:
    tenant_id = db.execute(
        text("insert into tenants (name) values ('Acme Components') returning id")
    ).scalar_one()
    user_id = db.execute(
        text(
            """
            insert into users (tenant_id, full_name, email, role)
            values (:tenant_id, 'Ada Lovelace', 'ada@example.com', 'user')
            returning id
            """
        ),
        {"tenant_id": tenant_id},
    ).scalar_one()
    conversation_id = db.execute(
        text(
            """
            insert into conversations (tenant_id, user_id, title)
            values (:tenant_id, :user_id, 'Late deliveries')
            returning id
            """
        ),
        {"tenant_id": tenant_id, "user_id": user_id},
    ).scalar_one()
    query_log_id = db.execute(
        text(
            """
            insert into query_log
                (tenant_id, user_id, conversation_id, question, query_text, verdict, result)
            values
                (:tenant_id, :user_id, :conversation_id,
                 'which vendors delivered late?', 'select 1', 'no_answer', 'succeeded')
            returning id
            """
        ),
        {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "conversation_id": conversation_id,
        },
    ).scalar_one()
    db.commit()

    db.execute(
        text("delete from conversations where id = :conversation_id"),
        {"conversation_id": conversation_id},
    )
    db.commit()

    row = db.execute(
        text("select conversation_id from query_log where id = :id"),
        {"id": query_log_id},
    ).one()
    assert row.conversation_id is None