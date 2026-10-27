"""The single data-access module: SQL for app data lives here and nowhere else.

Tenant isolation (conventions §6): every function that touches tenant-owned
data takes ``tenant_id`` as its first argument and filters on it inside the
SQL — including lookups by id and platform-admin paths.
"""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

##gemini 3.6 flash-task03-01
from datetime import datetime
from dataclasses import dataclass
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.orm import Session
###############################


def ping(session: Session) -> None:
    """Round-trip to the database. Raises on a broken connection."""
    session.execute(text("select 1"))


def ensure_tenant(session: Session, name: str) -> UUID:
    existing = session.execute(
        text(
            "select id from tenants where name = :name "
            "order by created_at, id limit 1"
        ),
        {"name": name},
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    return session.execute(
        text("insert into tenants (name, status) values (:name, 'active') returning id"),
        {"name": name},
    ).scalar_one()


def ensure_user(
    session: Session,
    tenant_id: UUID,
    full_name: str,
    email: str,
    role: str,
) -> UUID:
    existing = session.execute(
        text(
            "select id from users "
            "where tenant_id = :tenant_id and lower(email) = lower(:email)"
        ),
        {"tenant_id": tenant_id, "email": email},
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    return session.execute(
        text(
            "insert into users (tenant_id, full_name, email, role, status) "
            "values (:tenant_id, :full_name, :email, :role, 'active') returning id"
        ),
        {
            "tenant_id": tenant_id,
            "full_name": full_name,
            "email": email,
            "role": role,
        },
    ).scalar_one()


def ensure_platform_admin(session: Session, full_name: str, email: str) -> UUID:
    existing = session.execute(
        text(
            "select id from users "
            "where tenant_id is null and lower(email) = lower(:email)"
        ),
        {"email": email},
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    return session.execute(
        text(
            "insert into users (tenant_id, full_name, email, role, status) "
            "values (null, :full_name, :email, 'platform_admin', 'active') returning id"
        ),
        {"full_name": full_name, "email": email},
    ).scalar_one()


@dataclass(frozen=True, slots=True)
class UserRecord:
    id: UUID
    tenant_id: UUID | None
    full_name: str
    role: str
    status: str
    selected_tenant_id: UUID | None


def get_user_for_identity(session: Session, user_id: UUID) -> UserRecord | None:
    """Load the users row a token points at.

    Identity resolution happens before any Tenant context exists, so this is a
    deliberately named platform lookup rather than a tenant-scoped query.
    """
    row = session.execute(
        text(
            "select id, tenant_id, full_name, role, status, selected_tenant_id "
            "from users where id = :user_id"
        ),
        {"user_id": user_id},
    ).mappings().one_or_none()
    return UserRecord(**dict(row)) if row is not None else None


@dataclass(frozen=True, slots=True)
class PublicTenant:
    id: UUID
    name: str


def get_tenant_status(session: Session, tenant_id: UUID) -> str | None:
    """Tenant status for sign-in, before any tenant context exists.

    ``tenants`` is the Tenant itself, not tenant-owned data, so this is an
    explicitly named platform lookup rather than a tenant-scoped query.
    """
    return session.execute(
        text("select status from tenants where id = :tenant_id"),
        {"tenant_id": tenant_id},
    ).scalar_one_or_none()


@dataclass(frozen=True, slots=True)
class TenantRecord:
    id: UUID
    name: str
    status: str


def get_tenant(session: Session, tenant_id: UUID) -> TenantRecord | None:
    """Load one Tenant for identity/context resolution.

    ``tenants`` is the Tenant itself, not tenant-owned data, so this is an
    explicitly named platform lookup rather than a tenant-scoped query.
    """
    row = session.execute(
        text("select id, name, status from tenants where id = :tenant_id"),
        {"tenant_id": tenant_id},
    ).mappings().one_or_none()
    return TenantRecord(**dict(row)) if row is not None else None


def set_selected_tenant(
    session: Session, platform_admin_id: UUID, tenant_id: UUID
) -> None:
    """Point a Platform Admin at a Tenant. The caller commits.

    Only a Platform Admin row (no Tenant of its own) may hold a selection, so
    the role check is part of the SQL.
    """
    session.execute(
        text(
            "update users set selected_tenant_id = :tenant_id "
            "where id = :user_id and role = 'platform_admin' and tenant_id is null"
        ),
        {"tenant_id": tenant_id, "user_id": platform_admin_id},
    )


def clear_selected_tenant(session: Session, user_id: UUID) -> None:
    """Forget a Platform Admin's Selected Tenant. The caller commits."""
    session.execute(
        text(
            "update users set selected_tenant_id = null "
            "where id = :user_id and role = 'platform_admin'"
        ),
        {"user_id": user_id},
    )


def find_user_by_email(
    session: Session, tenant_id: UUID, email: str
) -> UserRecord | None:
    """Look a person up inside one Tenant; the Tenant filter is in the SQL."""
    row = session.execute(
        text(
            "select id, tenant_id, full_name, role, status, selected_tenant_id "
            "from users "
            "where tenant_id = :tenant_id and lower(email) = lower(:email)"
        ),
        {"tenant_id": tenant_id, "email": email},
    ).mappings().one_or_none()
    return UserRecord(**dict(row)) if row is not None else None


def find_platform_admin_by_email(session: Session, email: str) -> UserRecord | None:
    """The one deliberately platform-wide lookup: Platform Admins have no Tenant."""
    row = session.execute(
        text(
            "select id, tenant_id, full_name, role, status, selected_tenant_id "
            "from users "
            "where tenant_id is null and role = 'platform_admin' "
            "and lower(email) = lower(:email)"
        ),
        {"email": email},
    ).mappings().one_or_none()
    return UserRecord(**dict(row)) if row is not None else None


def list_active_tenants_public(session: Session) -> list[PublicTenant]:
    """Active Tenants only, id + name only — the sign-in dropdown's public read."""
    rows = session.execute(
        text(
            "select id, name from tenants "
            "where status = 'active' order by lower(name), id"
        )
    ).mappings().all()
    return [PublicTenant(**dict(row)) for row in rows]

#Start of Task 03-01
@dataclass(frozen=True, slots=True)
class TenantSummary:
    """One row of the Platform Admin's Tenants table."""

    id: UUID
    name: str
    status: str
    data_source_state: str
    user_count: int
    admin_email: str | None
    created_at: datetime


_TENANT_SUMMARY_SELECT = """
select
    t.id,
    t.name,
    t.status,
    coalesce(ds.status, 'not_connected') as data_source_state,
    (select count(*) from users u where u.tenant_id = t.id) as user_count,
    admin.email as admin_email,
    t.created_at
from tenants t
left join data_sources ds on ds.tenant_id = t.id
left join lateral (
    select u.email
    from users u
    where u.tenant_id = t.id and u.role = 'tenant_admin'
    order by u.created_at, u.id
    limit 1
) admin on true
"""


def list_tenants_for_platform_admin(
    session: Session, search: str | None, status: str
) -> list[TenantSummary]:
    """Every Tenant, optionally filtered. ``tenants`` is not tenant-owned data."""
    search = search.strip() if search else None
    conditions = ["(:status = 'all' or t.status = :status)"]
    params: dict[str, object] = {"status": status}
    if search:
        conditions.append("(t.name ilike :pattern or admin.email ilike :pattern)")
        params["pattern"] = f"%{search}%"
    rows = session.execute(
        text(
            _TENANT_SUMMARY_SELECT
            + " where "
            + " and ".join(conditions)
            + " order by lower(t.name), t.id"
        ),
        params,
    ).mappings().all()
    return [TenantSummary(**dict(row)) for row in rows]


def get_tenant_summary(session: Session, tenant_id: UUID) -> TenantSummary | None:
    row = session.execute(
        text(_TENANT_SUMMARY_SELECT + " where t.id = :tenant_id"),
        {"tenant_id": tenant_id},
    ).mappings().one_or_none()
    return TenantSummary(**dict(row)) if row is not None else None


def create_tenant_with_admin(
    session: Session, name: str, admin_full_name: str, admin_email: str
) -> TenantSummary:
    """Insert Tenant + first Tenant Admin + default settings; the caller commits."""
    tenant_id = session.execute(
        text("insert into tenants (name) values (:name) returning id"),
        {"name": name},
    ).scalar_one()
    session.execute(
        text(
            "insert into users (tenant_id, full_name, email, role, status) "
            "values (:tenant_id, :full_name, :email, 'tenant_admin', 'active')"
        ),
        {
            "tenant_id": tenant_id,
            "full_name": admin_full_name,
            "email": admin_email,
        },
    )
    session.execute(
        text(
            "insert into tenant_settings (tenant_id, maximum_period_days) "
            "values (:tenant_id, 730)"
        ),
        {"tenant_id": tenant_id},
    )
    summary = get_tenant_summary(session, tenant_id)
    if summary is None:
        raise RuntimeError("Tenant disappeared inside its creation transaction.")
    return summary


def update_tenant(
    session: Session,
    tenant_id: UUID,
    *,
    name: str | None = None,
    status: str | None = None,
) -> None:
    if name is not None:
        session.execute(
            text("update tenants set name = :name where id = :tenant_id"),
            {"name": name, "tenant_id": tenant_id},
        )
    if status is not None:
        session.execute(
            text("update tenants set status = :status where id = :tenant_id"),
            {"status": status, "tenant_id": tenant_id},
        )
        if status == "disabled":
            session.execute(
                text(
                    "update users set selected_tenant_id = null "
                    "where selected_tenant_id = :tenant_id"
                ),
                {"tenant_id": tenant_id},
            )


def get_first_tenant_admin_id(session: Session, tenant_id: UUID) -> UUID | None:
    return session.execute(
        text(
            "select id from users "
            "where tenant_id = :tenant_id and role = 'tenant_admin' "
            "order by created_at, id limit 1"
        ),
        {"tenant_id": tenant_id},
    ).scalar_one_or_none()


def email_taken_in_tenant(
    session: Session,
    tenant_id: UUID,
    email: str,
    *,
    exclude_user_id: UUID | None = None,
) -> bool:
    sql = (
        "select 1 from users where tenant_id = :tenant_id "
        "and lower(email) = lower(:email)"
    )
    params: dict[str, object] = {"tenant_id": tenant_id, "email": email}
    if exclude_user_id is not None:
        sql += " and id <> :exclude_user_id"
        params["exclude_user_id"] = exclude_user_id
    return (
        session.execute(text(sql + " limit 1"), params).scalar_one_or_none()
        is not None
    )


def set_tenant_admin_email(
    session: Session, tenant_id: UUID, email: str, full_name: str
) -> None:
    admin_id = get_first_tenant_admin_id(session, tenant_id)
    if admin_id is None:
        session.execute(
            text(
                "insert into users (tenant_id, full_name, email, role, status) "
                "values (:tenant_id, :full_name, :email, 'tenant_admin', 'active')"
            ),
            {"tenant_id": tenant_id, "full_name": full_name, "email": email},
        )
        return
    session.execute(
        text(
            "update users set email = :email "
            "where tenant_id = :tenant_id and id = :admin_id"
        ),
        {"email": email, "tenant_id": tenant_id, "admin_id": admin_id},
    )
#End of Task 03-01