"""Selected Tenant and context endpoints — HTTP seam only."""

from sqlalchemy import text

from tests.conftest import (
    auth,
    make_platform_admin,
    make_tenant,
    make_user,
    set_selected_tenant,
    signin_as,
)

_PLATFORM_MENUS = ["Conversations", "Tenants"]
_EXPANDED_MENUS = [
    "Conversations",
    "Tenants",
    "Datasets",
    "Charts",
    "Dashboards",
    "Data Source",
    "Model settings",
    "Semantic Layer",
    "Users",
    "Query Log",
]
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


def _selected_tenant_id(db, user_id):
    return db.execute(
        text("select selected_tenant_id from users where id = :user_id"),
        {"user_id": user_id},
    ).scalar_one()


class TestSelectingAndClearing:
    def test_platform_admin_selects_tenant(self, client, db):
        tenant = make_tenant(db, "Northwind Foods")
        admin_id = make_platform_admin(db)
        token = signin_as(db, client, admin_id)

        context = set_selected_tenant(client, token, tenant)

        assert context["tenant"] == {
            "id": str(tenant),
            "name": "Northwind Foods",
        }
        assert context["identity"]["role"] == "platform_admin"
        assert context["menus"] == _EXPANDED_MENUS
        assert _selected_tenant_id(db, admin_id) == tenant

        read_back = client.get("/api/context", headers=auth(token))
        assert read_back.status_code == 200
        assert read_back.json()["tenant"]["id"] == str(tenant)
        assert read_back.json()["menus"] == _EXPANDED_MENUS

    def test_platform_admin_clears_tenant(self, client, db):
        tenant = make_tenant(db, "Northwind Foods")
        admin_id = make_platform_admin(db)
        token = signin_as(db, client, admin_id)
        set_selected_tenant(client, token, tenant)

        response = client.delete("/api/context/tenant", headers=auth(token))

        assert response.status_code == 200
        assert _selected_tenant_id(db, admin_id) is None
        context = client.get("/api/context", headers=auth(token)).json()
        assert context["tenant"] is None
        assert context["menus"] == _PLATFORM_MENUS

    def test_selecting_unknown_tenant_is_rejected(self, client, db):
        admin_id = make_platform_admin(db)
        token = signin_as(db, client, admin_id)

        response = client.put(
            "/api/context/tenant",
            json={"tenant_id": "00000000-0000-0000-0000-000000000000"},
            headers=auth(token),
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"
        assert _selected_tenant_id(db, admin_id) is None

    def test_selecting_disabled_tenant_is_rejected(self, client, db):
        tenant = make_tenant(db, "Northwind Foods")
        db.execute(
            text("update tenants set status = 'disabled' where id = :tenant_id"),
            {"tenant_id": tenant},
        )
        db.commit()
        admin_id = make_platform_admin(db)
        token = signin_as(db, client, admin_id)

        response = client.put(
            "/api/context/tenant",
            json={"tenant_id": str(tenant)},
            headers=auth(token),
        )

        assert response.status_code == 403
        assert response.json()["error"]["code"] == "tenant_disabled"
        assert _selected_tenant_id(db, admin_id) is None

    def test_selection_survives_a_new_request(self, client, db):
        tenant = make_tenant(db, "Northwind Foods")
        admin_id = make_platform_admin(db)
        token = signin_as(db, client, admin_id)
        set_selected_tenant(client, token, tenant)

        for _ in range(3):
            response = client.get("/api/context", headers=auth(token))
            assert response.status_code == 200
            assert response.json()["tenant"]["id"] == str(tenant)


class TestTheContextGuard:
    def test_platform_admin_without_selection_sees_no_tenant(self, client, db):
        admin_id = make_platform_admin(db)
        token = signin_as(db, client, admin_id)

        response = client.get("/api/context", headers=auth(token))

        assert response.status_code == 200
        body = response.json()
        assert body["tenant"] is None
        assert body["menus"] == _PLATFORM_MENUS

    def test_selected_tenant_is_active(self, client, db):
        tenant = make_tenant(db, "Northwind Foods")
        admin_id = make_platform_admin(db)
        token = signin_as(db, client, admin_id)
        set_selected_tenant(client, token, tenant)

        db.execute(
            text("update tenants set status = 'disabled' where id = :tenant_id"),
            {"tenant_id": tenant},
        )
        db.commit()

        response = client.get("/api/context", headers=auth(token))

        assert response.status_code == 403
        assert response.json()["error"]["code"] == "tenant_disabled"
        assert _selected_tenant_id(db, admin_id) is None


class TestRoles:
    def test_tenant_roles_cannot_set_a_selected_tenant(self, client, db):
        tenant = make_tenant(db, "Northwind Foods")
        other = make_tenant(db, "Contoso")
        cases = (
            ("tenant_admin", "maria@northwind.test"),
            ("user", "omar@northwind.test"),
        )

        for role, email in cases:
            user_id = make_user(db, tenant, role, email)
            token = signin_as(db, client, user_id)

            put = client.put(
                "/api/context/tenant",
                json={"tenant_id": str(other)},
                headers=auth(token),
            )
            delete = client.delete("/api/context/tenant", headers=auth(token))

            assert put.status_code == 403, role
            assert delete.status_code == 403, role
            assert _selected_tenant_id(db, user_id) is None

    def test_tenant_users_context_is_always_their_own_tenant(self, client, db):
        tenant = make_tenant(db, "Northwind Foods")
        other = make_tenant(db, "Contoso")
        cases = (
            ("tenant_admin", "maria@northwind.test", _TENANT_ADMIN_MENUS),
            ("user", "omar@northwind.test", _USER_MENUS),
        )

        for role, email, menus in cases:
            user_id = make_user(db, tenant, role, email)
            token = signin_as(db, client, user_id)

            response = client.get(
                f"/api/context?tenant_id={other}", headers=auth(token)
            )

            assert response.status_code == 200, role
            body = response.json()
            assert body["tenant"] == {
                "id": str(tenant),
                "name": "Northwind Foods",
            }, role
            assert body["menus"] == menus, role
