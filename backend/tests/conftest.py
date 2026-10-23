"""Shared fixtures for the backend test suite.

Every test drives the HTTP API and asserts on the response and on database
state. ``db`` truncates every app table before each test, so this suite must
only ever point at a disposable database.
"""

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
            "jwt_secret": "test-jwt-secret",
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
