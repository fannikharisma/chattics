"""Sign-in, sign-out and the current user.

Sign-in is the one endpoint without an identity; it uses the explicitly named
platform lookups in ``repo`` instead of a tenant-context bypass. The token
carries the User id only, so role and status are re-read on every request
(ADR 0002).
"""

from typing import Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import create_token, get_current_identity
from app.config import Settings, get_settings
from app.db import get_session
from app.errors import AppError
from app.repo import (
    UserRecord,
    find_platform_admin_by_email,
    find_user_by_email,
    get_tenant_status,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

Role = Literal["platform_admin", "tenant_admin", "user"]

_MENUS_BY_ROLE: dict[str, list[str]] = {
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

_UNKNOWN_EMAIL_MESSAGE = (
    "No user with this email in that Tenant. "
    "Check the spelling or ask the Tenant Admin to add you."
)


class SignInRequest(BaseModel):
    tenant: UUID | Literal["platform"]
    email: str = Field(min_length=1)


class UserResponse(BaseModel):
    id: UUID
    full_name: str
    role: Role
    tenant_id: UUID | None


class SignInResponse(BaseModel):
    token: str
    user: UserResponse


class MeResponse(BaseModel):
    user: UserResponse
    menus: list[str]


def _user_response(user: UserRecord) -> UserResponse:
    return UserResponse(
        id=user.id,
        full_name=user.full_name,
        role=cast(Role, user.role),
        tenant_id=user.tenant_id,
    )


def menus_for_role(role: str) -> list[str]:
    """The backend's Menu list; the frontend renders this, not its own copy."""
    return list(_MENUS_BY_ROLE.get(role, []))


def _unknown_email() -> AppError:
    return AppError(
        "unknown_email",
        _UNKNOWN_EMAIL_MESSAGE,
        404,
        fields={"email": "Unknown email for this Tenant."},
    )


def _resolve_user(
    session: Session, tenant: UUID | Literal["platform"], email: str
) -> UserRecord:
    if tenant == "platform":
        user = find_platform_admin_by_email(session, email)
    else:
        status = get_tenant_status(session, tenant)
        # Checked before the email so a disabled Tenant cannot be probed.
        if status is not None and status != "active":
            raise AppError(
                "tenant_disabled",
                "This Tenant is disabled. Ask the Platform Admin to re-enable it.",
                403,
            )
        user = find_user_by_email(session, tenant, email)

    if user is None:
        raise _unknown_email()
    return user


@router.post("/sign-in", response_model=SignInResponse)
def sign_in(
    req: SignInRequest,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> SignInResponse:
    if not settings.test_mode_login:
        raise AppError(
            "test_mode_disabled",
            "Passwordless sign-in is turned off. Ask your administrator.",
            403,
        )

    user = _resolve_user(session, req.tenant, req.email.strip().lower())

    if user.status != "active":
        raise AppError(
            "user_deactivated",
            "This account is deactivated. Ask an administrator to reactivate it.",
            403,
        )

    return SignInResponse(
        token=create_token(user.id, settings),
        user=_user_response(user),
    )


@router.post("/sign-out", status_code=204)
def sign_out() -> Response:
    """The frontend owns the cookie; the backend has nothing to revoke."""
    return Response(status_code=204)


@router.get("/me", response_model=MeResponse)
def me(identity: UserRecord = Depends(get_current_identity)) -> MeResponse:
    return MeResponse(
        user=_user_response(identity),
        menus=menus_for_role(identity.role),
    )