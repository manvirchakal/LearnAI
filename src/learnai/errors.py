"""Typed error hierarchy and exception handlers.

Replaces the 41 bare ``except Exception`` blocks in the old ``server/main.py``,
several of which leaked ``str(e)`` straight to the client (e.g. ``:1000``,
``:2109``, ``:2310``, ``:2439``). The rule going forward: services raise a
typed ``AppError`` subclass; nothing outside the two handlers below catches
broadly (enforced by ruff's ``BLE001`` — see ``pyproject.toml``).

Responses follow RFC 7807 (``application/problem+json``).
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from learnai.logging import get_request_id

logger = structlog.get_logger(__name__)


class AppError(Exception):
    """Base for every error a service is allowed to raise on purpose."""

    status_code: int = 500
    code: str = "internal_error"

    def __init__(self, message: str, *, detail: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail or {}


class NotFound(AppError):
    """A resource doesn't exist *for this user*.

    Deliberately the same response whether the resource doesn't exist at all
    or belongs to someone else — see ``ScopedRepository`` in the data-model
    plan. No 403 exists for "wrong owner"; that would be an existence oracle.
    """

    status_code = 404
    code = "not_found"


class ValidationError(AppError):
    status_code = 422
    code = "validation_error"


class Forbidden(AppError):
    status_code = 403
    code = "forbidden"


class RateLimited(AppError):
    status_code = 429
    code = "rate_limited"


class UpstreamError(AppError):
    """A downstream dependency (Anthropic, Qdrant, Mongo, an OpenAI-compatible
    endpoint) failed in a way the caller can potentially retry."""

    status_code = 502
    code = "upstream_error"


class StorageError(AppError):
    status_code = 500
    code = "storage_error"


def _problem_response(status_code: int, code: str, message: str, request: Request) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        media_type="application/problem+json",
        content={
            "type": f"https://learnai.dev/errors/{code}",
            "title": code.replace("_", " "),
            "status": status_code,
            "detail": message,
            "request_id": get_request_id(),
        },
        headers={"X-Request-ID": get_request_id()},
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        if exc.status_code >= 500:
            logger.error("app_error", code=exc.code, message=exc.message, detail=exc.detail)
        else:
            logger.info("app_error", code=exc.code, message=exc.message)
        return _problem_response(exc.status_code, exc.code, exc.message, request)

    # Registered against Starlette's base HTTPException, not fastapi.HTTPException
    # (a subclass): Starlette's own routing layer raises the base class directly
    # for route-not-found / method-not-allowed, and a handler registered for the
    # subclass would not match a base-class instance. Registering against the
    # base catches both the framework's own routing errors and any
    # `fastapi.HTTPException` application code raises, since the subclass is
    # still an instance of the base.
    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = "not_found" if exc.status_code == 404 else "http_error"
        return _problem_response(exc.status_code, code, str(exc.detail), request)

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        # The only place a bare `Exception` may be caught. Never leaks `str(exc)`
        # to the client — full detail goes to the log, keyed by request_id.
        logger.error("unhandled_exception", exc_info=exc)
        return _problem_response(500, "internal_error", "An unexpected error occurred.", request)
