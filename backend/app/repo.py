"""The single data-access module: SQL for app data lives here and nowhere else.

Tenant isolation (conventions §6): every function that touches tenant-owned
data takes ``tenant_id`` as its first argument and filters on it inside the
SQL — including lookups by id and platform-admin paths.
"""

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