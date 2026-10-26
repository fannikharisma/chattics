# """The one public read: active Tenants for the sign-in dropdown."""

# from uuid import UUID

# from fastapi import APIRouter, Depends
# from pydantic import BaseModel
# from sqlalchemy.orm import Session

# from app.db import get_session
# from app.repo import list_active_tenants_public

# router = APIRouter(prefix="/api/tenants", tags=["tenants"])


# class TenantPublicResponse(BaseModel):
#     id: UUID
#     name: str


# @router.get("/public", response_model=list[TenantPublicResponse])
# def tenants_public(
#     session: Session = Depends(get_session),
# ) -> list[TenantPublicResponse]:
#     return [
#         TenantPublicResponse(id=tenant.id, name=tenant.name)
#         for tenant in list_active_tenants_public(session)
#     ]

#Start of Task 03-01
"""Platform Admin Tenant management plus the one public read.

The public route feeds the sign-in dropdown. Every other route requires a
Platform Admin.
"""

import re
from datetime import datetime
from typing import Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import require_platform_admin
from app.db import get_session
from app.errors import AppError
from app.repo import (
    TenantSummary,
    UserRecord,
    create_tenant_with_admin,
    email_taken_in_tenant,
    get_first_tenant_admin_id,
    get_tenant_summary,
    list_active_tenants_public,
    list_tenants_for_platform_admin,
    set_tenant_admin_email,
    update_tenant,
)

router = APIRouter(prefix="/api/tenants", tags=["tenants"])

TenantStatus = Literal["active", "disabled"]
DataSourceState = Literal["connected", "not_connected"]
StatusFilter = Literal["all", "active", "disabled"]

_EMAIL_SHAPE = re.compile(r"^[^@\s]+@[^@\s]+$")
_NAME_MESSAGE = "Enter a Tenant name."
_CREATE_EMAIL_MESSAGE = "Enter the first Tenant Admin's email, like name@company.com."
_EDIT_EMAIL_MESSAGE = "Enter the Tenant Admin's email, like name@company.com."


class TenantPublicResponse(BaseModel):
    id: UUID
    name: str


class TenantResponse(BaseModel):
    id: UUID
    name: str
    status: TenantStatus
    data_source_state: DataSourceState
    user_count: int
    admin_email: str | None
    created_at: datetime


class TenantCreateRequest(BaseModel):
    name: str
    admin_email: str


class TenantUpdateRequest(BaseModel):
    name: str | None = None
    admin_email: str | None = None
    status: TenantStatus | None = None


def _invalid(fields: dict[str, str]) -> AppError:
    return AppError(
        "validation_error",
        "Some fields need your attention.",
        422,
        fields=fields,
    )


def _not_found() -> AppError:
    return AppError("not_found", "This Tenant could not be found.", 404)


def _validate_new_tenant(payload: TenantCreateRequest) -> tuple[str, str]:
    fields: dict[str, str] = {}
    name = payload.name.strip()
    if not name:
        fields["name"] = _NAME_MESSAGE
    email = payload.admin_email.strip().lower()
    if not _EMAIL_SHAPE.match(email):
        fields["admin_email"] = _CREATE_EMAIL_MESSAGE
    if fields:
        raise _invalid(fields)
    return name, email


def _validate_tenant_changes(
    payload: TenantUpdateRequest,
) -> tuple[str | None, str | None]:
    fields: dict[str, str] = {}
    name = None
    email = None
    if payload.name is not None:
        name = payload.name.strip()
        if not name:
            fields["name"] = _NAME_MESSAGE
    if payload.admin_email is not None:
        email = payload.admin_email.strip().lower()
        if not _EMAIL_SHAPE.match(email):
            fields["admin_email"] = _EDIT_EMAIL_MESSAGE
    if fields:
        raise _invalid(fields)
    return name, email


def _admin_full_name(email: str) -> str:
    words = re.split(r"[._-]+", email.split("@", 1)[0])
    return " ".join(word.capitalize() for word in words if word) or "Tenant Admin"


def _tenant_response(tenant: TenantSummary) -> TenantResponse:
    return TenantResponse(
        id=tenant.id,
        name=tenant.name,
        status=cast(TenantStatus, tenant.status),
        data_source_state=cast(DataSourceState, tenant.data_source_state),
        user_count=tenant.user_count,
        admin_email=tenant.admin_email,
        created_at=tenant.created_at,
    )


@router.get("/public", response_model=list[TenantPublicResponse])
def tenants_public(
    session: Session = Depends(get_session),
) -> list[TenantPublicResponse]:
    return [
        TenantPublicResponse(id=tenant.id, name=tenant.name)
        for tenant in list_active_tenants_public(session)
    ]


@router.get("", response_model=list[TenantResponse])
def list_tenants(
    search: str | None = Query(default=None),
    status_filter: StatusFilter = Query(default="all", alias="status"),
    _identity: UserRecord = Depends(require_platform_admin),
    session: Session = Depends(get_session),
) -> list[TenantResponse]:
    tenants = list_tenants_for_platform_admin(session, search, status_filter)
    return [_tenant_response(tenant) for tenant in tenants]


@router.post("", response_model=TenantResponse, status_code=201)
def create_tenant(
    payload: TenantCreateRequest,
    _identity: UserRecord = Depends(require_platform_admin),
    session: Session = Depends(get_session),
) -> TenantResponse:
    name, email = _validate_new_tenant(payload)
    try:
        tenant = create_tenant_with_admin(
            session, name, _admin_full_name(email), email
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    return _tenant_response(tenant)


@router.get("/{tenant_id}", response_model=TenantResponse)
def tenant_details(
    tenant_id: UUID,
    _identity: UserRecord = Depends(require_platform_admin),
    session: Session = Depends(get_session),
) -> TenantResponse:
    tenant = get_tenant_summary(session, tenant_id)
    if tenant is None:
        raise _not_found()
    return _tenant_response(tenant)


@router.patch("/{tenant_id}", response_model=TenantResponse)
def edit_tenant(
    tenant_id: UUID,
    payload: TenantUpdateRequest,
    _identity: UserRecord = Depends(require_platform_admin),
    session: Session = Depends(get_session),
) -> TenantResponse:
    name, email = _validate_tenant_changes(payload)
    if get_tenant_summary(session, tenant_id) is None:
        raise _not_found()

    try:
        if email is not None:
            admin_id = get_first_tenant_admin_id(session, tenant_id)
            if email_taken_in_tenant(
                session, tenant_id, email, exclude_user_id=admin_id
            ):
                message = "That email already belongs to another User in this Tenant."
                raise AppError(
                    "email_in_use",
                    message,
                    409,
                    fields={"admin_email": message},
                )
        update_tenant(session, tenant_id, name=name, status=payload.status)
        if email is not None:
            set_tenant_admin_email(
                session, tenant_id, email, _admin_full_name(email)
            )
        session.commit()
    except Exception:
        session.rollback()
        raise

    updated = get_tenant_summary(session, tenant_id)
    if updated is None:
        raise _not_found()
    return _tenant_response(updated)

#End of Task 03-01