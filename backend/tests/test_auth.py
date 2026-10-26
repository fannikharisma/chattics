"""Auth endpoint tests — HTTP seam only."""

from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy import text

from app.config import get_settings
from app.main import app
from tests.conftest import (
    make_platform_admin,
    make_tenant,
    make_user,
    signin,
)

_PLATFORM_MENUS = ["Conversations", "Tenants"]
_TENANT_ADMIN_MENUS = [
    "Conversations",
    "Datasets",
    "Charts",
    "Dashboards",
    "Data Source",
    "Model settings",
    "Semantic Layer",
    "Users",
    "Query Log",
]
_USER_MENUS = ["Conversations", "Datasets", "Charts", "Dashboards"]


class TestSignInHappyPaths:
    def test_tenant_user_can_sign_in_with_email_only(self, client, db):
        tenant = make_tenant(db)
        user_id = make_user(db, tenant, "user", "omar@northwind.test")

        response = client.post(
            "/api/auth/sign-in",
            json={"tenant": str(tenant), "email": "omar@northwind.test"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["token"]
        assert body["user"] == {
            "id": str(user_id),
            "full_name": "Omar",
            "role": "user",
            "tenant_id": str(tenant),
        }
        assert set(body) == {"token", "user"}
        assert set(body["user"]) == {"id", "full_name", "role", "tenant_id"}

    def test_platform_entry_signs_in_platform_admin(self, client, db):
        admin_id = make_platform_admin(db, "platform@chattics.test")

        response = client.post(
            "/api/auth/sign-in",
            json={"tenant": "platform", "email": "platform@chattics.test"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["user"]["id"] == str(admin_id)
        assert body["user"]["role"] == "platform_admin"
        assert body["user"]["tenant_id"] is None

    def test_sign_in_is_case_insensitive_on_email(self, client, db):
        tenant = make_tenant(db)
        user_id = make_user(db, tenant, "tenant_admin", "MARIA@NORTHWIND.TEST")

        token = signin(client, tenant, "maria@northwind.test")

        response = client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["user"]["id"] == str(user_id)


class TestSignInRejections:
    def test_unknown_email_returns_unknown_email_error(self, client, db):
        tenant = make_tenant(db)

        response = client.post(
            "/api/auth/sign-in",
            json={"tenant": str(tenant), "email": "nobody@northwind.test"},
        )

        assert response.status_code == 404
        body = response.json()
        error = body["error"]
        assert error["code"] == "unknown_email"
        assert "Check the spelling" in error["message"]
        assert "Tenant Admin" in error["message"]
        assert error["fields"] == {"email": "Unknown email for this Tenant."}
        assert "token" not in body

    def test_email_from_another_tenant_does_not_sign_in(self, client, db):
        tenant_a = make_tenant(db, "Northwind Foods")
        tenant_b = make_tenant(db, "Contoso")
        make_user(db, tenant_b, "user", "omar@contoso.test")

        response = client.post(
            "/api/auth/sign-in",
            json={"tenant": str(tenant_a), "email": "omar@contoso.test"},
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "unknown_email"

    def test_deactivated_user_cannot_sign_in(self, client, db):
        tenant = make_tenant(db)
        make_user(db, tenant, "user", "omar@northwind.test", status="deactivated")

        response = client.post(
            "/api/auth/sign-in",
            json={"tenant": str(tenant), "email": "omar@northwind.test"},
        )

        assert response.status_code == 403
        body = response.json()
        assert body["error"]["code"] == "user_deactivated"
        assert "token" not in body

    def test_test_mode_off_blocks_passwordless_sign_in(self, client, db, settings):
        tenant = make_tenant(db)
        make_user(db, tenant, "user", "omar@northwind.test")
        app.dependency_overrides[get_settings] = lambda: settings.model_copy(
            update={"test_mode_login": False}
        )

        response = client.post(
            "/api/auth/sign-in",
            json={"tenant": str(tenant), "email": "omar@northwind.test"},
        )

        assert response.status_code == 403
        body = response.json()
        assert body["error"]["code"] == "test_mode_disabled"
        assert "token" not in body


class TestMe:
    def test_me_returns_role_menus(self, client, db):
        cases = (
            ("platform_admin", _PLATFORM_MENUS),
            ("tenant_admin", _TENANT_ADMIN_MENUS),
            ("user", _USER_MENUS),
        )
        for role, expected_menus in cases:
            tenant = make_tenant(db, f"Tenant {role}")
            if role == "platform_admin":
                email = "platform@chattics.test"
                make_platform_admin(db, email)
                selector = "platform"
            else:
                email = f"{role}@northwind.test"
                make_user(db, tenant, role, email)
                selector = tenant

            token = signin(client, selector, email)
            response = client.get(
                "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
            )

            assert response.status_code == 200, role
            body = response.json()
            assert body["user"]["role"] == role
            assert body["menus"] == expected_menus, role
            assert set(body) == {"user", "menus"}

    def test_unauthenticated_request_is_rejected(self, client, db, settings):
        tenant = make_tenant(db)
        user_id = make_user(db, tenant, "user", "omar@northwind.test")
        now = datetime.now(timezone.utc)
        expired = jwt.encode(
            {
                "sub": str(user_id),
                "iat": now - timedelta(hours=2),
                "exp": now - timedelta(hours=1),
            },
            settings.jwt_secret,
            algorithm="HS256",
        )

        responses = [
            client.get("/api/auth/me"),
            client.get(
                "/api/auth/me", headers={"Authorization": "Bearer not-a-token"}
            ),
            client.get(
                "/api/auth/me", headers={"Authorization": f"Bearer {expired}"}
            ),
        ]

        for response in responses:
            assert response.status_code == 401
            error = response.json()["error"]
            assert error["code"] == "invalid_session"
            assert "sign in again" in error["message"]

    def test_token_claims_do_not_grant_roles(self, client, db, settings):
        tenant = make_tenant(db)
        user_id = make_user(db, tenant, "user", "omar@northwind.test")
        now = datetime.now(timezone.utc)
        forged = jwt.encode(
            {
                "sub": str(user_id),
                "role": "platform_admin",
                "iat": now,
                "exp": now + timedelta(hours=1),
            },
            settings.jwt_secret,
            algorithm="HS256",
        )

        response = client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {forged}"}
        )

        assert response.status_code == 200
        body = response.json()
        assert body["user"]["role"] == "user"
        assert body["menus"] == _USER_MENUS

    def test_deactivated_after_sign_in_is_rejected_immediately(self, client, db):
        tenant = make_tenant(db)
        user_id = make_user(db, tenant, "user", "omar@northwind.test")
        token = signin(client, tenant, "omar@northwind.test")

        db.execute(
            text("update users set status = 'deactivated' where id = :user_id"),
            {"user_id": user_id},
        )

        response = client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "invalid_session"


class TestPublicTenants:
    def test_public_tenants_lists_only_active_tenant_names(self, client, db):
        make_tenant(db, "Northwind Foods")
        make_tenant(db, "Contoso")
        make_tenant(db, "Old Tenant")
        db.execute(
            text("update tenants set status = 'disabled' where name = 'Old Tenant'")
        )

        response = client.get("/api/tenants/public")

        assert response.status_code == 200
        tenants = response.json()
        assert [tenant["name"] for tenant in tenants] == ["Contoso", "Northwind Foods"]
        assert all(set(tenant) == {"id", "name"} for tenant in tenants)