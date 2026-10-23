"""App exceptions and the single error envelope.

Every non-2xx response leaves the API in this shape (conventions §4):

    {"error": {"code": "...", "message": "...", "fields": {...}}}

``code`` is stable and snake_case, ``message`` is plain English a non-technical
person can act on, and ``fields`` appears only for form validation errors.
Register the handlers once, in ``main.py``, with ``register_error_handlers``.
"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

_INTERNAL_MESSAGE = "Something went wrong. Please try again."

_HTTP_CODES = {
    401: "unauthenticated",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
}


class AppError(Exception):
    """An error we chose to show. Anything else is unexpected and becomes 500."""

    def __init__(
        self,
        code: str,
        message: str,
        status: int = 400,
        fields: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.fields = fields


def _error_response(
    code: str,
    message: str,
    status: int,
    fields: dict[str, str] | None = None,
) -> JSONResponse:
    error: dict[str, Any] = {"code": code, "message": message}
    if fields:
        error["fields"] = fields
    return JSONResponse(status_code=status, content={"error": error})


async def _app_error(request: Request, exc: AppError) -> JSONResponse:
    return _error_response(exc.code, exc.message, exc.status, exc.fields)


async def _validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    fields: dict[str, str] = {}
    for error in exc.errors():
        parts = [str(part) for part in error["loc"] if part not in ("body", "query", "path")]
        fields.setdefault(".".join(parts) or "request", error["msg"])
    return _error_response(
        "validation_error",
        "Some fields need your attention.",
        422,
        fields,
    )


async def _http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) else "The request could not be completed."
    return _error_response(
        _HTTP_CODES.get(exc.status_code, "http_error"),
        message,
        exc.status_code,
    )


async def _unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    # Log the type and route only: messages and SQL can carry secrets or Query text.
    logger.error(
        "unhandled error on %s %s (%s)",
        request.method,
        request.url.path,
        type(exc).__name__,
    )
    return _error_response("internal_error", _INTERNAL_MESSAGE, 500)


def register_error_handlers(app: FastAPI) -> None:
    """Wire every error path to the one envelope. Call once, right after creating the app."""
    app.add_exception_handler(AppError, _app_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(Exception, _unexpected_error)