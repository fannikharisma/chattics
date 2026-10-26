"""The one public read: active Tenants for the sign-in dropdown."""

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_session
from app.repo import list_active_tenants_public

router = APIRouter(prefix="/api/tenants", tags=["tenants"])


class TenantPublicResponse(BaseModel):
    id: UUID
    name: str


@router.get("/public", response_model=list[TenantPublicResponse])
def tenants_public(
    session: Session = Depends(get_session),
) -> list[TenantPublicResponse]:
    return [
        TenantPublicResponse(id=tenant.id, name=tenant.name)
        for tenant in list_active_tenants_public(session)
    ]