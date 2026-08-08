"""Typed error hierarchy.

Replaces the 41 bare ``except Exception`` blocks in the old ``server/main.py``,
several of which leaked ``str(e)`` straight to the client (e.g. ``:1000``,
``:2109``, ``:2310``, ``:2439``). The rule going forward: services raise a
typed ``AppError`` subclass; nothing outside ``http_errors.py``'s two handlers
catches broadly (enforced by ruff's ``BLE001`` — see ``pyproject.toml``).

Deliberately framework-free — no FastAPI/Starlette imports. Every layer
(repositories, services, routers) raises these; only ``http_errors.py``
(imported solely by ``main.py``) knows how to turn one into an HTTP response.
Importing FastAPI here would trip the "services must not depend on the web
framework" import-linter contract the moment any service raises an AppError.
"""

from __future__ import annotations

from typing import Any


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


class Unauthenticated(AppError):
    """No valid credentials presented: missing/expired/invalid session, or a
    Google ID token that fails verification. Distinct from ``Forbidden`` —
    that's a known identity lacking permission; this is no identity at all.
    """

    status_code = 401
    code = "unauthenticated"


class Forbidden(AppError):
    status_code = 403
    code = "forbidden"


class RateLimited(AppError):
    status_code = 429
    code = "rate_limited"


class Conflict(AppError):
    """The resource exists but isn't in a state the request can act on yet —
    e.g. reading a material's document tree before its TOC job has finished.
    Distinct from ``ValidationError``: the request itself is well-formed,
    the resource's current state just isn't ready for it. The client's
    correct response is to poll (see ``GET /api/v1/jobs/{id}``) and retry."""

    status_code = 409
    code = "conflict"


class UpstreamError(AppError):
    """A downstream dependency (Anthropic, Qdrant, Mongo, an OpenAI-compatible
    endpoint) failed in a way the caller can potentially retry."""

    status_code = 502
    code = "upstream_error"


class StorageError(AppError):
    status_code = 500
    code = "storage_error"
