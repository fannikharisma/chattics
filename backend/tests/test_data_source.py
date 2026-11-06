"""The Data Source card through the HTTP seam, using the fake connector."""

from sqlalchemy import text

from app.connectors import get_connector_factory
from app.connectors.fake import FakeConnector
from app.main import app
from tests.conftest import (
    auth,
    make_platform_admin,
    make_tenant,
    make_user,
    set_selected_tenant,
    signin_as,
)

_FIELDS = {
    "engine": "Google BigQuery",
    "method": "Local Google sign-in",
    "project_id": "demo-project",
    "dataset": "demo_dataset",
}


def _tenant_admin_token(client, db, tenant, email="maria@northwind.test"):
    user_id = make_user(db, tenant, "tenant_admin", email)
    return signin_as(db, client, user_id)


def _test(client, token, fields=None):
    return client.post(
        "/api/data-source/test",
        json=fields if fields is not None else _FIELDS,
        headers=auth(token),
    )


def _save(client, token, fields=None):
    return client.put(
        "/api/data-source",
        json=fields if fields is not None else _FIELDS,
        headers=auth(token),
    )


def _connect(client, token, fields=None):
    tested = _test(client, token, fields)
    assert tested.status_code == 200, tested.text
    saved = _save(client, token, fields)
    assert saved.status_code == 200, saved.text
    return saved


class TestTheSelectedTenantGuard:
    def test_platform_admin_without_selection_gets_no_selected_tenant(
        self, client, db
    ):
        admin_id = make_platform_admin(db)
        token = signin_as(db, client, admin_id)

        response = client.get("/api/data-source", headers=auth(token))

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "no_selected_tenant"

    def test_platform_admin_uses_selected_tenant_data_source(self, client, db):
        tenant_a = make_tenant(db, "Northwind Foods")
        tenant_b = make_tenant(db, "Contoso")
        token_a = _tenant_admin_token(client, db, tenant_a, "maria@northwind.test")
        token_b = _tenant_admin_token(client, db, tenant_b, "alex@contoso.test")

        _connect(
            client,
            token_a,
            _FIELDS | {"project_id": "project-a", "dataset": "dataset_a"},
        )
        _connect(
            client,
            token_b,
            _FIELDS | {"project_id": "project-b", "dataset": "dataset_b"},
        )

        platform_id = make_platform_admin(db)
        platform_token = signin_as(db, client, platform_id)
        set_selected_tenant(client, platform_token, tenant_b)

        response = client.get("/api/data-source", headers=auth(platform_token))

        assert response.status_code == 200
        assert response.json()["fields"] == {
            "project_id": "project-b",
            "dataset": "dataset_b",
        }


class TestTestConnection:
    def test_test_connection_returns_four_passing_checks_and_tables(
        self, client, db
    ):
        tenant = make_tenant(db)
        token = _tenant_admin_token(client, db, tenant)

        response = _test(client, token)

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "not_connected"
        assert [item["key"] for item in body["checklist"]] == [
            "signed_in",
            "project_found",
            "dataset_found",
            "read_only",
        ]
        assert all(item["passed"] for item in body["checklist"])
        assert body["error"] is None
        assert {
            table["name"]: table["column_count"] for table in body["tables"]
        } == {
            "dim_vendor": 3,
            "fact_monthly_forecast": 3,
            "fact_monthly_po": 5,
        }

        row = db.execute(
            text(
                "select status, test_fingerprint, tested_at "
                "from data_sources where tenant_id = :tenant_id"
            ),
            {"tenant_id": tenant},
        ).mappings().one()
        assert row["status"] == "not_connected"
        assert row["test_fingerprint"]
        assert row["tested_at"] is not None

    def test_test_connection_failure_is_plain_and_partial(self, client, db):
        tenant = make_tenant(db)
        token = _tenant_admin_token(client, db, tenant)
        app.dependency_overrides[get_connector_factory] = (
            lambda: lambda fields: FakeConnector(fail_at="dataset_found")
        )

        response = _test(client, token)

        assert response.status_code == 200
        body = response.json()
        assert [item["key"] for item in body["checklist"]] == [
            "signed_in",
            "project_found",
            "dataset_found",
        ]
        assert [item["passed"] for item in body["checklist"]] == [
            True,
            True,
            False,
        ]
        assert body["tables"] == []
        assert "dataset" in body["error"].lower()
        assert "Traceback" not in body["error"]
        assert db.execute(text("select count(*) from data_sources")).scalar_one() == 0

    def test_test_connection_requires_tenant_admin(self, client, db):
        tenant = make_tenant(db)
        user_id = make_user(db, tenant, "user", "omar@northwind.test")
        user_token = signin_as(db, client, user_id)
        platform_id = make_platform_admin(db)
        platform_token = signin_as(db, client, platform_id)

        as_user = _test(client, user_token)
        as_platform = _test(client, platform_token)

        assert as_user.status_code == 403
        assert as_platform.status_code == 409
        assert as_platform.json()["error"]["code"] == "no_selected_tenant"


class TestTestBeforeSave:
    def test_save_without_a_test_is_rejected(self, client, db):
        tenant = make_tenant(db)
        token = _tenant_admin_token(client, db, tenant)

        response = _save(client, token)

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "test_required"
        assert db.execute(text("select count(*) from data_sources")).scalar_one() == 0

    def test_save_after_passing_test_succeeds(self, client, db):
        tenant = make_tenant(db)
        token = _tenant_admin_token(client, db, tenant)
        assert _test(client, token).status_code == 200

        response = _save(client, token)

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "connected"
        assert body["tested_at"] is not None
        status = db.execute(
            text("select status from data_sources where tenant_id = :tenant_id"),
            {"tenant_id": tenant},
        ).scalar_one()
        assert status == "connected"

    def test_editing_fields_after_test_invalidates_save(self, client, db):
        tenant = make_tenant(db)
        token = _tenant_admin_token(client, db, tenant)
        assert (
            _test(client, token, _FIELDS | {"dataset": "dataset_a"}).status_code
            == 200
        )

        response = _save(client, token, _FIELDS | {"dataset": "dataset_b"})

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "test_required"
        row = db.execute(
            text(
                "select status, fields from data_sources "
                "where tenant_id = :tenant_id"
            ),
            {"tenant_id": tenant},
        ).mappings().one()
        assert row["status"] == "not_connected"
        assert row["fields"]["dataset"] == "dataset_a"

    def test_client_cannot_forge_the_fingerprint(self, client, db):
        tenant = make_tenant(db)
        token = _tenant_admin_token(client, db, tenant)

        response = _save(
            client, token, _FIELDS | {"test_fingerprint": "deadbeef"}
        )

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "test_required"
        assert db.execute(text("select count(*) from data_sources")).scalar_one() == 0


class TestIsolationAndValidation:
    def test_each_tenant_has_at_most_one_data_source(self, client, db):
        tenant_a = make_tenant(db, "Northwind Foods")
        token = _tenant_admin_token(client, db, tenant_a)
        _connect(client, token)

        second = _save(client, token)

        assert second.status_code == 200
        rows = db.execute(
            text(
                "select tenant_id, count(*) as total "
                "from data_sources group by tenant_id"
            )
        ).all()
        assert [(row.tenant_id, row.total) for row in rows] == [(tenant_a, 1)]

    def test_unknown_engine_is_rejected(self, client, db):
        tenant = make_tenant(db)
        token = _tenant_admin_token(client, db, tenant)

        response = _test(client, token, _FIELDS | {"engine": "snowflake"})

        assert response.status_code == 400
        assert response.json()["error"]["code"] == "unknown_engine"
        assert db.execute(text("select count(*) from data_sources")).scalar_one() == 0

    def test_saved_fields_are_not_secret(self, client, db):
        tenant = make_tenant(db)
        token = _tenant_admin_token(client, db, tenant)
        _connect(client, token)

        fields = db.execute(
            text("select fields from data_sources where tenant_id = :tenant_id"),
            {"tenant_id": tenant},
        ).scalar_one()

        assert set(fields) == {"project_id", "dataset"}
        assert all("secret" not in value.lower() for value in fields.values())

class TestConnectionFields:
    def test_fields_are_declared_by_the_connector(self, client, db):
        tenant = make_tenant(db)
        token = _tenant_admin_token(client, db, tenant)

        response = client.get("/api/data-source/fields", headers=auth(token))

        assert response.status_code == 200
        fields = response.json()["fields"]
        assert [field["key"] for field in fields] == [
            "engine",
            "method",
            "project_id",
            "dataset",
        ]

        engine = fields[0]
        assert engine["kind"] == "select"
        assert [
            option["label"]
            for option in engine["options"]
            if not option["disabled"]
        ] == ["Google BigQuery"]
        assert "PostgreSQL (later)" in [
            option["label"]
            for option in engine["options"]
            if option["disabled"]
        ]

        method = fields[1]
        assert method["options"][0]["label"] == (
            "Local Google sign-in (test and demo only)"
        )

        assert fields[2]["kind"] == "text"
        assert fields[2]["placeholder"] == "my-company-analytics"

    def test_fields_require_tenant_admin(self, client, db):
        tenant = make_tenant(db)
        user_id = make_user(db, tenant, "user", "omar@northwind.test")
        token = signin_as(db, client, user_id)

        response = client.get("/api/data-source/fields", headers=auth(token))

        assert response.status_code == 403