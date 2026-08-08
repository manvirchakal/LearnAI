"""Turns ``AppError``s (and everything else) into RFC 7807 responses.

Split out from ``errors.py`` specifically to keep FastAPI/Starlette imports
out of that module — ``errors.py`` is imported by services and repositories,
which must not depend on the web framework (see the import-linter contracts
in ``pyproject.toml`). This module is imported by ``main.py`` only.
"""

from __future__ import annotations

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from learnai.errors import AppError
from learnai.logging import get_request_id

logger = structlog.get_logger(__name__)


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
