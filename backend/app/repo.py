"""The single data-access module: SQL for app data lives here and nowhere else.

Tenant isolation (conventions §6): every function that touches tenant-owned
data takes ``tenant_id`` as its first argument and filters on it inside the
SQL — including lookups by id and platform-admin paths.
"""

from sqlalchemy import text
from sqlalchemy.orm import Session


def ping(session: Session) -> None:
    """Round-trip to the database. Raises on a broken connection."""
    session.execute(text("select 1"))