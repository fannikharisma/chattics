"""Tenants management tests — HTTP seam only."""

from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.main import app
from tests.conftest import (
    make_platform_admin,
    make_tenant,
    make_user,
    signin,
)


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class TestCreateTenant:
    def test_platform_admin_creates_tenant_with_first_admin(
        self, client: TestClient, db: Session
    ) -> None:
        make_platform_admin(db)
        token = signin(client, "platform", "platform@chattics.test")

        response = client.post(
            "/api/tenants",
            json={"name": "Northwind Foods", "admin_email": "maria@northwind.test"},
            headers=_auth(token),
        )

        assert response.status_code == 201
        body = response.json()
        tenant_id = UUID(body["id"])
        assert body["name"] == "Northwind Foods"
        assert body["status"] == "active"
        assert body["data_source_state"] == "not_connected"
        assert body["user_count"] == 1
        assert body["admin_email"] == "maria@northwind.test"
        assert body["created_at"]

        # Assert DB state
        tenant_row = db.execute(
            text("select status from tenants where id = :id"), {"id": tenant_id}
        ).one()
        assert tenant_row.status == "active"

        users = db.execute(
            text(
                "select email, role, full_name from users where tenant_id = :tenant_id"
            ),
            {"tenant_id": tenant_id},
        ).mappings().all()
        assert len(users) == 1
        assert users[0]["email"] == "maria@northwind.test"
        assert users[0]["role"] == "tenant_admin"

        settings_count = db.execute(
            text(
                "select maximum_period_days from tenant_settings "
                "where tenant_id = :tenant_id"
            ),
            {"tenant_id": tenant_id},
        ).scalar_one()
        assert settings_count == 730

    def test_create_rejects_blank_name_and_bad_email(
        self, client: TestClient, db: Session
    ) -> None:
        make_platform_admin(db)
        token = signin(client, "platform", "platform@chattics.test")

        response = client.post(
            "/api/tenants",
            json={"name": "   ", "admin_email": "not-an-email"},
            headers=_auth(token),
        )

        assert response.status_code == 422
        error = response.json()["error"]
        assert error["code"] == "validation_error"
        assert "name" in error["fields"]
        assert "admin_email" in error["fields"]

        # Assert no database state changed
        tenant_count = db.execute(text("select count(*) from tenants")).scalar_one()
        assert tenant_count == 0

    def test_create_is_atomic(self, client: TestClient, db: Session) -> None:
        make_platform_admin(db)
        token = signin(client, "platform", "platform@chattics.test")

        # Force a database failure on tenant_settings insert
        db.execute(
            text(
                """
                create or replace function fail_tenant_settings() returns trigger
                language plpgsql as $$ begin raise exception 'forced failure'; end $$;
                create trigger fail_tenant_settings before insert on tenant_settings
                for each row execute function fail_tenant_settings();
                """
            )
        )
        db.commit()

        try:
            strict_client = TestClient(app, raise_server_exceptions=False)
            response = strict_client.post(
                "/api/tenants",
                json={
                    "name": "Atomic Foods",
                    "admin_email": "admin@atomic.test",
                },
                headers=_auth(token),
            )
            assert response.status_code == 500
        finally:
            db.execute(
                text(
                    "drop trigger if exists fail_tenant_settings on tenant_settings;"
                    "drop function if exists fail_tenant_settings();"
                )
            )
            db.commit()

        assert db.execute(text("select count(*) from tenants")).scalar_one() == 0
        assert (
            db.execute(
                text("select count(*) from users where tenant_id is not null")
            ).scalar_one()
            == 0
        )


class TestListSearchFilter:
    def test_list_returns_counts_and_data_source_state(
        self, client: TestClient, db: Session
    ) -> None:
        make_platform_admin(db)
        token = signin(client, "platform", "platform@chattics.test")

        t1 = make_tenant(db, "Tenant One")
        make_user(db, t1, role="tenant_admin", email="admin1@t1.test")
        make_user(db, t1, role="user", email="user1@t1.test")
        make_user(db, t1, role="user", email="user2@t1.test")

        # Connect data source for t1
        db.execute(
            text(
                "insert into data_sources (tenant_id, engine, method, status) "
                "values (:tenant_id, 'bigquery', 'google_local', 'connected')"
            ),
            {"tenant_id": t1},
        )

        t2 = make_tenant(db, "Tenant Two")
        make_user(db, t2, role="tenant_admin", email="admin2@t2.test")
        db.commit()

        response = client.get("/api/tenants", headers=_auth(token))
        assert response.status_code == 200
        rows = response.json()
        assert len(rows) == 2

        t1_data = next(r for r in rows if r["id"] == str(t1))
        assert t1_data["user_count"] == 3
        assert t1_data["data_source_state"] == "connected"

        t2_data = next(r for r in rows if r["id"] == str(t2))
        assert t2_data["user_count"] == 1
        assert t2_data["data_source_state"] == "not_connected"

    def test_search_matches_tenant_name_and_admin_email(
        self, client: TestClient, db: Session
    ) -> None:
        make_platform_admin(db)
        token = signin(client, "platform", "platform@chattics.test")

        t1 = make_tenant(db, "Northwind Foods")
        make_user(db, t1, role="tenant_admin", email="maria@northwind.test")

        t2 = make_tenant(db, "Acme Corp")
        make_user(db, t2, role="tenant_admin", email="wile@acme.test")
        db.commit()

        # Match name
        r1 = client.get("/api/tenants?search=north", headers=_auth(token))
        assert r1.status_code == 200
        assert [t["id"] for t in r1.json()] == [str(t1)]

        # Match email
        r2 = client.get("/api/tenants?search=maria@", headers=_auth(token))
        assert r2.status_code == 200
        assert [t["id"] for t in r2.json()] == [str(t1)]

        # No match returns empty list
        r3 = client.get("/api/tenants?search=xyz999", headers=_auth(token))
        assert r3.status_code == 200
        assert r3.json() == []

    def test_status_filter(self, client: TestClient, db: Session) -> None:
        make_platform_admin(db)
        token = signin(client, "platform", "platform@chattics.test")

        t1 = make_tenant(db, "Active Tenant")
        t2 = make_tenant(db, "Disabled Tenant")
        db.execute(
            text("update tenants set status = 'disabled' where id = :id"),
            {"id": t2},
        )
        db.commit()

        all_res = client.get("/api/tenants?status=all", headers=_auth(token))
        assert len(all_res.json()) == 2

        act_res = client.get("/api/tenants?status=active", headers=_auth(token))
        assert len(act_res.json()) == 1
        assert act_res.json()[0]["id"] == str(t1)

        dis_res = client.get("/api/tenants?status=disabled", headers=_auth(token))
        assert len(dis_res.json()) == 1
        assert dis_res.json()[0]["id"] == str(t2)


class TestEditTenant:
    def test_edit_name_and_admin_email(
        self, client: TestClient, db: Session
    ) -> None:
        make_platform_admin(db)
        token = signin(client, "platform", "platform@chattics.test")

        t_id = make_tenant(db, "Old Name")
        make_user(db, t_id, role="tenant_admin", email="oldadmin@test.com")
        db.commit()

        response = client.patch(
            f"/api/tenants/{t_id}",
            json={"name": "New Name", "admin_email": "newadmin@test.com"},
            headers=_auth(token),
        )

        assert response.status_code == 200
        body = response.json()
        assert body["name"] == "New Name"
        assert body["admin_email"] == "newadmin@test.com"
        assert body["user_count"] == 1

        # Confirm DB state
        name = db.execute(
            text("select name from tenants where id = :id"), {"id": t_id}
        ).scalar_one()
        assert name == "New Name"

        user_count = db.execute(
            text("select count(*) from users where tenant_id = :id"),
            {"id": t_id},
        ).scalar_one()
        assert user_count == 1

    def test_edit_rejects_invalid_values(
        self, client: TestClient, db: Session
    ) -> None:
        make_platform_admin(db)
        token = signin(client, "platform", "platform@chattics.test")

        t_id = make_tenant(db, "Valid Name")
        make_user(db, t_id, role="tenant_admin", email="valid@test.com")
        db.commit()

        response = client.patch(
            f"/api/tenants/{t_id}",
            json={"name": "   ", "admin_email": "bad-email"},
            headers=_auth(token),
        )

        assert response.status_code == 422
        error = response.json()["error"]
        assert error["code"] == "validation_error"
        assert "name" in error["fields"]
        assert "admin_email" in error["fields"]


class TestDisableReEnable:
    def test_disable_blocks_user_sign_in(
        self, client: TestClient, db: Session
    ) -> None:
        t_id = make_tenant(db, "Target Tenant")
        make_user(db, t_id, role="user", email="user@target.test")
        make_platform_admin(db)
        token = signin(client, "platform", "platform@chattics.test")

        # Disable tenant
        patch_res = client.patch(
            f"/api/tenants/{t_id}",
            json={"status": "disabled"},
            headers=_auth(token),
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["status"] == "disabled"

        # Attempt sign in as user
        sign_res = client.post(
            "/api/auth/sign-in",
            json={"tenant": str(t_id), "email": "user@target.test"},
        )
        assert sign_res.status_code == 403
        body = sign_res.json()
        assert body["error"]["code"] == "tenant_disabled"

    def test_reenable_restores_sign_in(
        self, client: TestClient, db: Session
    ) -> None:
        t_id = make_tenant(db, "Disabled Tenant")
        make_user(db, t_id, role="user", email="user@disabled.test")
        db.execute(
            text("update tenants set status = 'disabled' where id = :id"),
            {"id": t_id},
        )
        make_platform_admin(db)
        token = signin(client, "platform", "platform@chattics.test")

        # Re-enable tenant
        patch_res = client.patch(
            f"/api/tenants/{t_id}",
            json={"status": "active"},
            headers=_auth(token),
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["status"] == "active"

        # Sign in succeeds
        sign_res = client.post(
            "/api/auth/sign-in",
            json={"tenant": str(t_id), "email": "user@disabled.test"},
        )
        assert sign_res.status_code == 200
        assert sign_res.json()["token"]

    def test_disable_deletes_nothing(
        self, client: TestClient, db: Session
    ) -> None:
        t_id = make_tenant(db, "Full Tenant")
        u_id = make_user(db, t_id, role="user", email="u@full.test")
        db.execute(
            text(
                "insert into conversations (id, tenant_id, user_id, title) "
                "values (gen_random_uuid(), :tenant_id, :user_id, 'Conv')"
            ),
            {"tenant_id": t_id, "user_id": u_id},
        )
        db.execute(
            text(
                "insert into query_log (id, tenant_id, user_id, question, query_text, verdict, result) "
                "values (gen_random_uuid(), :tenant_id, :user_id, 'Q', 'SELECT 1', 'confirmed', 'succeeded')"
            ),
            {"tenant_id": t_id, "user_id": u_id},
        )
        db.commit()

        make_platform_admin(db)
        token = signin(client, "platform", "platform@chattics.test")

        client.patch(
            f"/api/tenants/{t_id}",
            json={"status": "disabled"},
            headers=_auth(token),
        )

        assert (
            db.execute(
                text("select count(*) from users where tenant_id = :id"),
                {"id": t_id},
            ).scalar_one()
            == 1
        )
        assert (
            db.execute(
                text("select count(*) from conversations where tenant_id = :id"),
                {"id": t_id},
            ).scalar_one()
            == 1
        )
        assert (
            db.execute(
                text("select count(*) from query_log where tenant_id = :id"),
                {"id": t_id},
            ).scalar_one()
            == 1
        )

    def test_disable_clears_platform_admin_selected_tenant(
        self, client: TestClient, db: Session
    ) -> None:
        t_id = make_tenant(db, "Selected Tenant")
        pa_id = make_platform_admin(db)
        db.execute(
            text(
                "update users set selected_tenant_id = :t_id where id = :pa_id"
            ),
            {"t_id": t_id, "pa_id": pa_id},
        )
        db.commit()

        token = signin(client, "platform", "platform@chattics.test")

        client.patch(
            f"/api/tenants/{t_id}",
            json={"status": "disabled"},
            headers=_auth(token),
        )

        sel = db.execute(
            text("select selected_tenant_id from users where id = :pa_id"),
            {"pa_id": pa_id},
        ).scalar_one_or_none()
        assert sel is None


class TestPermissionsAndIsolation:
    def test_non_platform_roles_cannot_use_tenant_admin_endpoints(
        self, client: TestClient, db: Session
    ) -> None:
        t_id = make_tenant(db)
        make_user(db, t_id, role="tenant_admin", email="ta@test.com")
        make_user(db, t_id, role="user", email="u@test.com")

        tokens = [
            signin(client, t_id, "ta@test.com"),
            signin(client, t_id, "u@test.com"),
        ]

        endpoints = [
            ("GET", "/api/tenants"),
            ("POST", "/api/tenants"),
            ("GET", f"/api/tenants/{t_id}"),
            ("PATCH", f"/api/tenants/{t_id}"),
        ]

        for token in tokens:
            headers = _auth(token)
            for method, url in endpoints:
                if method == "GET":
                    res = client.get(url, headers=headers)
                elif method == "POST":
                    res = client.post(
                        url,
                        json={"name": "Bad", "admin_email": "bad@test.com"},
                        headers=headers,
                    )
                elif method == "PATCH":
                    res = client.patch(
                        url, json={"name": "Bad"}, headers=headers
                    )
                assert res.status_code == 403

    def test_creating_a_tenant_never_touches_another_tenants_data(
        self, client: TestClient, db: Session
    ) -> None:
        t1 = make_tenant(db, "Tenant One")
        make_user(db, t1, role="user", email="user1@t1.test")
        make_platform_admin(db)
        token = signin(client, "platform", "platform@chattics.test")

        res = client.post(
            "/api/tenants",
            json={"name": "Tenant Two", "admin_email": "admin2@t2.test"},
            headers=_auth(token),
        )
        assert res.status_code == 201
        t2_id = UUID(res.json()["id"])

        # Tenant 1 users unmodified
        t1_users = (
            db.execute(
                text("select email from users where tenant_id = :id"),
                {"id": t1},
            )
            .scalars()
            .all()
        )
        assert t1_users == ["user1@t1.test"]

        # Tenant 2 user belongs to Tenant 2 only
        t2_users = (
            db.execute(
                text(
                    "select email, tenant_id from users where tenant_id = :id"
                ),
                {"id": t2_id},
            )
            .mappings()
            .all()
        )
        assert len(t2_users) == 1
        assert t2_users[0]["email"] == "admin2@t2.test"
        assert t2_users[0]["tenant_id"] == t2_id