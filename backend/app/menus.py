"""The one Menu mapping, shared by /auth/me and /context.

The backend owns which Menus a role gets; the frontend only maps labels to
routes. A Platform Admin working inside a Tenant gets the Tenant Admin Menus on
top of Tenants, because they may do everything that Tenant's people can.
"""

from typing import Literal

Role = Literal["platform_admin", "tenant_admin", "user"]

MENUS_BY_ROLE: dict[str, list[str]] = {
    "platform_admin": ["Conversations", "Tenants"],
    "tenant_admin": [
        "Conversations",
        "Datasets",
        "Charts",
        "Dashboards",
        "Data Source",
        "Model settings",
        "Semantic Layer",
        "Users",
        "Query Log",
    ],
    "user": ["Conversations", "Datasets", "Charts", "Dashboards"],
}


def menus_for_role(role: str) -> list[str]:
    """The role's own Menu list, used when no Tenant context is needed."""
    return list(MENUS_BY_ROLE.get(role, []))


def menus_for_context(role: str, working_in_tenant: bool) -> list[str]:
    """The Menu list for a request's actual Tenant context."""
    if role == "platform_admin" and working_in_tenant:
        tenant_menus = MENUS_BY_ROLE["tenant_admin"]
        # "add the Tenant Admin and User Menus"; Conversations already exists.
        return list(MENUS_BY_ROLE["platform_admin"]) + [
            label for label in tenant_menus if label not in MENUS_BY_ROLE["platform_admin"]
        ]
    return menus_for_role(role)
