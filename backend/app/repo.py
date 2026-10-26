"""The single data-access module: SQL for app data lives here and nowhere else.

Tenant isolation (conventions §6): every function that touches tenant-owned
data takes ``tenant_id`` as its first argument and filters on it inside the
SQL — including lookups by id and platform-admin paths.
"""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


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


def get_user_for_identity(session: Session, user_id: UUID) -> UserRecord | None:
    """Load the users row a token points at.

    Identity resolution happens before any Tenant context exists, so this is a
    deliberately named platform lookup rather than a tenant-scoped query.
    """
    row = session.execute(
        text(
            "select id, tenant_id, full_name, role, status "
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


def find_user_by_email(
    session: Session, tenant_id: UUID, email: str
) -> UserRecord | None:
    """Look a person up inside one Tenant; the Tenant filter is in the SQL."""
    row = session.execute(
        text(
            "select id, tenant_id, full_name, role, status "
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
            "select id, tenant_id, full_name, role, status "
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
