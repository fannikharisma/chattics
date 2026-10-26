"""Shared fixtures for the backend test suite.

Every test drives the HTTP API and asserts on the response and on database
state. ``db`` truncates every app table before each test, so this suite must
only ever point at a disposable database.
"""

import uuid
from collections.abc import Iterator

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from app.ai import FakeAI, get_ai
from app.config import Settings, get_settings
from app.connectors.fake import FakeConnector
from app.db import build_engine, build_session_factory, get_session
from app.main import app
from app.repo import ensure_platform_admin, ensure_tenant, ensure_user

_TABLES = (
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
)


@pytest.fixture(scope="session")
def settings() -> Settings:
    """Test settings: the test database, throwaway secrets, test-mode sign-in."""
    real = get_settings()
    return real.model_copy(
        update={
            "database_url": real.test_database_url,
            "jwt_secret": "test-jwt-secret-0123456789abcdef",
            "encryption_key": Fernet.generate_key().decode(),
            "test_mode_login": True,
            "environment": "test",
        }
    )


@pytest.fixture(scope="session")
def test_engine(settings: Settings) -> Iterator[Engine]:
    engine = build_engine(settings.test_database_url)
    yield engine
    engine.dispose()


@pytest.fixture()
def db(test_engine: Engine) -> Iterator[Session]:
    """A session on the test database, with empty tables, closed after the test."""
    with build_session_factory(test_engine)() as session:
        session.execute(
            text(f"TRUNCATE {', '.join(_TABLES)} RESTART IDENTITY CASCADE")
        )
        session.commit()
        yield session


@pytest.fixture()
def fake_connector() -> FakeConnector:
    return FakeConnector()


@pytest.fixture()
def fake_ai() -> FakeAI:
    return FakeAI()


@pytest.fixture()
def client(settings: Settings, db: Session, fake_ai: FakeAI) -> Iterator[TestClient]:
    """The app with its real edges replaced by test doubles and the test database."""
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_session] = lambda: db
    app.dependency_overrides[get_ai] = lambda: fake_ai
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def make_tenant(db: Session, name: str = "Northwind Foods") -> uuid.UUID:
    """Insert an active Tenant and return its id."""
    return ensure_tenant(db, name)


def make_user(
    db: Session,
    tenant_id: uuid.UUID,
    role: str = "user",
    email: str | None = None,
    status: str = "active",
    full_name: str | None = None,
) -> uuid.UUID:
    """Insert a User in a Tenant, optionally deactivated, and return its id."""
    email = email or f"{role}@northwind.test"
    if full_name is None:
        full_name = email.split("@")[0].replace(".", " ").replace("_", " ").title()
    user_id = ensure_user(db, tenant_id, full_name, email, role)
    if status != "active":
        db.execute(
            text("update users set status = :status where id = :user_id"),
            {"status": status, "user_id": user_id},
        )
    return user_id


def make_platform_admin(
    db: Session,
    email: str = "platform@chattics.test",
    status: str = "active",
) -> uuid.UUID:
    """Insert a Platform Admin with no Tenant and return its id."""
    user_id = ensure_platform_admin(db, "Platform Admin", email)
    if status != "active":
        db.execute(
            text("update users set status = :status where id = :user_id"),
            {"status": status, "user_id": user_id},
        )
    return user_id


def signin(client: TestClient, tenant: uuid.UUID | str, email: str) -> str:
    """POST /api/auth/sign-in, assert success, return the token."""
    response = client.post(
        "/api/auth/sign-in",
        json={"tenant": str(tenant), "email": email},
    )
    assert response.status_code == 200, response.text
    token = response.json()["token"]
    assert token
    return token