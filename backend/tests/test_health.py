from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.db import get_session
from app.main import app


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "chattics-backend"}


def test_health_db_reports_ok(client: TestClient) -> None:
    response = client.get("/api/health/db")
    assert response.status_code == 200
    assert response.json() == {"database": "ok"}


class _UnreachableSession:
    """Stands in for a session whose database has gone away."""

    def execute(self, *args: object, **kwargs: object) -> None:
        raise OperationalError("select 1", {}, RuntimeError("connection refused"))


def test_health_db_failure_is_plain_and_standard(client: TestClient) -> None:
    app.dependency_overrides[get_session] = lambda: _UnreachableSession()

    response = client.get("/api/health/db")

    assert response.status_code == 503
    body = response.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == "database_unreachable"
    assert "database" in body["error"]["message"].lower()
    assert "fields" not in body["error"]

    text = response.text.lower()
    for leak in ("operationalerror", "traceback", "postgres", "password", "psycopg"):
        assert leak not in text