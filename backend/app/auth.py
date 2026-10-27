"""Identity resolution and session tokens.

A token carries only the User id. Role, Tenant and status are read from the
users row on every request, so deactivating a User takes effect immediately
(ADR 0002).
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_session
from app.errors import AppError
from app.repo import (
    TenantRecord,
    UserRecord,
    clear_selected_tenant,
    get_tenant,
    get_user_for_identity,
)

_ALGORITHM = "HS256"
_TOKEN_LIFETIME = timedelta(hours=12)
_INVALID_SESSION = "Your session is not valid. Please sign in again."


def _invalid_session() -> AppError:
    return AppError("invalid_session", _INVALID_SESSION, 401)


def _forbidden() -> AppError:
    return AppError("forbidden", "You do not have access to this page.", 403)


def _no_selected_tenant() -> AppError:
    return AppError(
        "no_selected_tenant",
        "Choose the Tenant you want to work in first.",
        409,
    )


def create_token(user_id: UUID, settings: Settings | None = None) -> str:
    """Sign a 12-hour token whose only identity claim is the User id."""
    if settings is None:
        settings = get_settings()
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": str(user_id),
            "iat": now,
            "exp": now + _TOKEN_LIFETIME,
        },
        settings.jwt_secret,
        algorithm=_ALGORITHM,
    )


def decode_token(token: str, settings: Settings | None = None) -> UUID:
    """Verify signature and expiry, then return the User id."""
    if settings is None:
        settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[_ALGORITHM],
            options={"require": ["sub", "exp"]},
        )
        return UUID(str(payload["sub"]))
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
        raise _invalid_session() from None


def get_current_identity(
    request: Request,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> UserRecord:
    """Resolve Authorization: Bearer <token> to an active users row."""
    authorization = request.headers.get("Authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise _invalid_session()

    user_id = decode_token(token.strip(), settings)
    user = get_user_for_identity(session, user_id)
    if user is None or user.status != "active":
        raise _invalid_session()
    return user


def _resolve_tenant_context(
    identity: UserRecord, session: Session, *, require_selection: bool
) -> TenantRecord | None:
    """The one place "Platform Admin in a Tenant" differs from "own Tenant"."""
    if identity.role == "platform_admin":
        if identity.selected_tenant_id is None:
            if require_selection:
                raise _no_selected_tenant()
            return None
        tenant = get_tenant(session, identity.selected_tenant_id)
        if tenant is None:
            clear_selected_tenant(session, identity.id)
            session.commit()
            if require_selection:
                raise _no_selected_tenant()
            return None
        if tenant.status != "active":
            clear_selected_tenant(session, identity.id)
            session.commit()
            raise AppError(
                "tenant_disabled",
                "This Tenant is disabled. Choose another Tenant to work in.",
                403,
            )
        return tenant

    if identity.tenant_id is None:
        raise _forbidden()
    tenant = get_tenant(session, identity.tenant_id)
    if tenant is None or tenant.status != "active":
        raise AppError(
            "tenant_disabled",
            "This Tenant is disabled. Ask the Platform Admin to re-enable it.",
            403,
        )
    return tenant


def get_tenant_context(
    identity: UserRecord = Depends(get_current_identity),
    session: Session = Depends(get_session),
) -> TenantRecord:
    """The Tenant a tenant-scoped request acts in.

    A Platform Admin acts inside their Selected Tenant; everyone else inside
    their own. Every tenant-scoped endpoint depends on this and passes its
    ``id`` to ``repo``. A missing selection is a conflict, a disabled Tenant
    is forbidden.
    """
    tenant = _resolve_tenant_context(identity, session, require_selection=True)
    if tenant is None:  # require_selection guarantees a Tenant
        raise _no_selected_tenant()
    return tenant


def get_optional_tenant_context(
    identity: UserRecord, session: Session
) -> TenantRecord | None:
    """The Tenant shown by /api/context; a Platform Admin may have none yet."""
    return _resolve_tenant_context(identity, session, require_selection=False)


def require_platform_admin(
    identity: UserRecord = Depends(get_current_identity),
) -> UserRecord:
    if identity.role != "platform_admin":
        raise _forbidden()
    return identity


def require_tenant_admin(
    identity: UserRecord = Depends(get_current_identity),
) -> UserRecord:
    # A Platform Admin can do everything a Tenant Admin can inside the Selected
    # Tenant; ticket 04's tenant_context decides which Tenant that is.
    if identity.role not in ("tenant_admin", "platform_admin"):
        raise _forbidden()
    return identity


def require_user(
    identity: UserRecord = Depends(get_current_identity),
) -> UserRecord:
    # Every role can use the User Menus on its own data.
    return identity
