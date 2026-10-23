"""Create the local demo Tenant and sign-in accounts.

Run manually from backend/:
    uv run python -m scripts.seed_local

Never import this at application startup. It only creates missing rows; it does
not modify or delete existing data.
"""

from app import repo
from app.config import get_settings
from app.db import SessionLocal

TENANT_NAME = "Northwind Foods"

ACCOUNTS = (
    ("Maria Chen", "maria@northwind.test", "tenant_admin"),
    ("Omar Haddad", "omar@northwind.test", "user"),
)


def main() -> None:
    settings = get_settings()
    if settings.environment != "local":
        raise SystemExit(
            "seed_local.py only runs with ENVIRONMENT=local. "
            "Refusing to touch this database."
        )

    with SessionLocal() as session:
        tenant_id = repo.ensure_tenant(session, TENANT_NAME)
        for full_name, email, role in ACCOUNTS:
            repo.ensure_user(session, tenant_id, full_name, email, role)
        repo.ensure_platform_admin(session, "Dana Ortiz", "platform@chattics.test")
        session.commit()

    print(f"Tenant: {TENANT_NAME}")
    print("Sign-in accounts (no password in test mode):")
    print("  Tenant Admin   maria@northwind.test")
    print("  User           omar@northwind.test")
    print("  Platform Admin platform@chattics.test")
    print("Existing rows were left unchanged.")


if __name__ == "__main__":
    main()