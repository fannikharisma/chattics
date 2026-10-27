"""The signed-in shell's context: who am I, which Tenant, which Menus.

``GET`` is a read for every role. A Platform Admin with no Selected Tenant
sees ``tenant: null`` and only the Tenants Menu. ``PUT`` and ``DELETE`` change
the selection and are Platform Admin only. The Selected Tenant is never put in
the token; every read comes from the users row.
"""

from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import (
    get_current_identity,
    get_optional_tenant_context,
    require_platform_admin,
)
from app.db import get_session
from app.errors import AppError
from app.menus import Role, menus_for_context
from app.repo import (
    TenantRecord,
    UserRecord,
    clear_selected_tenant,
    get_tenant,
    set_selected_tenant,
)

router = APIRouter(prefix="/api/context", tags=["context"])


class ContextIdentity(BaseModel):
    id: UUID
    full_name: str
    role: Role


class ContextTenant(BaseModel):
    id: UUID
    name: str


class ContextResponse(BaseModel):
    identity: ContextIdentity
    tenant: ContextTenant | None
    menus: list[str]


class SelectedTenantRequest(BaseModel):
    tenant_id: UUID


def _tenant_response(tenant: TenantRecord | None) -> ContextTenant | None:
    if tenant is None:
        return None
    return ContextTenant(id=tenant.id, name=tenant.name)


def _context_response(
    identity: UserRecord, tenant: TenantRecord | None
) -> ContextResponse:
    return ContextResponse(
        identity=ContextIdentity(
            id=identity.id,
            full_name=identity.full_name,
            role=cast(Role, identity.role),
        ),
        tenant=_tenant_response(tenant),
        menus=menus_for_context(identity.role, tenant is not None),
    )


def _tenant_disabled() -> AppError:
    return AppError(
        "tenant_disabled",
        "This Tenant is disabled. Choose another Tenant to work in.",
        403,
    )


@router.get("", response_model=ContextResponse)
def read_context(
    identity: UserRecord = Depends(get_current_identity),
    session: Session = Depends(get_session),
) -> ContextResponse:
    tenant = get_optional_tenant_context(identity, session)
    return _context_response(identity, tenant)


@router.put("/tenant", response_model=ContextResponse)
def select_tenant(
    payload: SelectedTenantRequest,
    identity: UserRecord = Depends(require_platform_admin),
    session: Session = Depends(get_session),
) -> ContextResponse:
    tenant = get_tenant(session, payload.tenant_id)
    if tenant is None:
        raise AppError(
            "not_found",
            "This Tenant could not be found.",
            404,
        )
    if tenant.status != "active":
        raise _tenant_disabled()

    set_selected_tenant(session, identity.id, tenant.id)
    session.commit()
    return _context_response(identity, tenant)


@router.delete("/tenant", response_model=ContextResponse)
def clear_tenant(
    identity: UserRecord = Depends(require_platform_admin),
    session: Session = Depends(get_session),
) -> ContextResponse:
    clear_selected_tenant(session, identity.id)
    session.commit()
    return _context_response(identity, None)
