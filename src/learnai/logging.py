"""Structured logging.

Replaces ``logging.basicConfig(level=logging.DEBUG)`` from the old
``server/main.py:110`` (unstructured, DEBUG in production, no request
correlation) and the 11 bare ``print()`` calls that bypassed logging
entirely. Every log line carries a request id via a contextvar, so a single
request's logs can be grepped out of a busy production stream.
"""

from __future__ import annotations

import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Any, cast

import structlog

from learnai.config import Environment, Settings

_request_id: ContextVar[str] = ContextVar("request_id", default="-")


def new_request_id() -> str:
    return uuid.uuid4().hex[:16]


def bind_request_id(request_id: str) -> None:
    _request_id.set(request_id)


def get_request_id() -> str:
    return _request_id.get()


def _add_request_id(_logger: object, _method: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    event_dict["request_id"] = get_request_id()
    return event_dict


def configure_logging(settings: Settings) -> None:
    level = logging.DEBUG if settings.environment is Environment.development else logging.INFO

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        _add_request_id,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    renderer: Any
    if settings.environment is Environment.production:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Route stdlib logging (uvicorn, third-party libs) through the same pipeline
    # instead of a second, differently-formatted stream.
    logging.basicConfig(level=level, handlers=[], force=True)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return cast(structlog.stdlib.BoundLogger, structlog.get_logger(name))
