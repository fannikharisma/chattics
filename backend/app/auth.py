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
from app.repo import UserRecord, get_user_for_identity

_ALGORITHM = "HS256"
_TOKEN_LIFETIME = timedelta(hours=12)
_INVALID_SESSION = "Your session is not valid. Please sign in again."


def _invalid_session() -> AppError:
    return AppError("invalid_session", _INVALID_SESSION, 401)


def _forbidden() -> AppError:
    return AppError("forbidden", "You do not have access to this page.", 403)


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
