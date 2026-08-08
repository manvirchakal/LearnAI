"""Application factory.

Everything that touched the network or the filesystem at *import time* in the
old ``server/main.py`` — the Bedrock/S3/Textract/etc. client construction at
``:70-108`` and, worst of all, the Cognito JWKS fetch at ``:154`` that made
the process unable to start without network access — happens here instead,
inside ``lifespan``, exactly once, after the app has already started
accepting connections for liveness checks.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

import anthropic
import openai
import redis.asyncio as redis
import structlog
from arq.connections import ArqRedis
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from qdrant_client import AsyncQdrantClient

from learnai.config import Settings, get_settings
from learnai.db.migrations import ALL_MIGRATIONS, apply_pending
from learnai.db.mongo import create_mongo_client, get_database
from learnai.db.mongo import ping as mongo_ping
from learnai.http_errors import register_exception_handlers
from learnai.logging import bind_request_id, configure_logging, get_logger, new_request_id
from learnai.routers.auth import router as auth_router
from learnai.routers.collections import router as collections_router
from learnai.routers.jobs import router as jobs_router
from learnai.routers.materials import router as materials_router
from learnai.routers.profile import router as profile_router
from learnai.services.extraction.anthropic_pdf import AnthropicPDFExtractor
from learnai.services.extraction.base import DocumentExtractor
from learnai.services.llm.anthropic_client import AnthropicLLMClient
from learnai.services.llm.client import LLMClient
from learnai.services.llm.openai_compat_client import OpenAICompatLLMClient
from learnai.services.storage.base import StorageBackend
from learnai.services.storage.local import LocalFilesystemStorage


def _build_storage(settings: Settings) -> StorageBackend:
    if settings.storage_backend == "local":
        return LocalFilesystemStorage(settings.storage_root)
    # MinIOStorage is the documented escape hatch for clusters with no
    # ReadWriteMany PVC (see the plan) but isn't built yet — fail loudly at
    # startup rather than silently falling back to local storage.
    raise NotImplementedError(
        f"storage_backend={settings.storage_backend!r} is not implemented yet"
    )


def _build_llm_client(
    settings: Settings,
) -> tuple[LLMClient, anthropic.AsyncAnthropic | openai.AsyncOpenAI]:
    """The generation client (narrative, game idea/code, diagrams, chat,
    translation) — provider-agnostic per ``settings.llm_backend``. Ingestion
    (native PDF reading) is a separate, always-Anthropic concern and isn't
    built yet; this is only the text-in/text-out generation path.

    Returns the adapter plus the raw SDK client, so ``lifespan`` can close
    the latter on shutdown without the adapter needing to expose that.
    """
    if settings.llm_backend == "anthropic":
        sdk_client = anthropic.AsyncAnthropic(
            api_key=settings.generation_api_key(), base_url=settings.llm_base_url
        )
        return AnthropicLLMClient(sdk_client, settings), sdk_client
    openai_client = openai.AsyncOpenAI(
        api_key=settings.generation_api_key() or "not-needed",
        base_url=settings.llm_base_url,
    )
    return OpenAICompatLLMClient(openai_client, settings), openai_client


def _build_extractor(
    settings: Settings,
) -> tuple[DocumentExtractor, anthropic.AsyncAnthropic]:
    """Document extraction (native PDF reading) is always Anthropic —
    independent of ``settings.llm_backend``, which only governs the
    provider-agnostic generation client above. Its own client because the
    generation backend may not even be Anthropic."""
    sdk_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key.get_secret_value())
    return AnthropicPDFExtractor(sdk_client, settings), sdk_client


logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings)
    log = get_logger(__name__)

    log.info("startup_begin", environment=settings.environment)

    mongo_client = create_mongo_client(settings)
    app.state.mongo_client = mongo_client
    app.state.mongo_db = get_database(mongo_client, settings)

    # Best-effort, not fatal: if Mongo isn't reachable yet (e.g. mid rolling
    # restart), the process still starts — /health/ready correctly reports
    # mongo=false until it recovers, and the orchestrator's restart-on-failed-
    # readiness handles retrying, rather than this crash-looping the pod.
    try:
        applied = await apply_pending(app.state.mongo_db, ALL_MIGRATIONS)
        if applied:
            log.info("migrations_applied", migration_ids=applied)
    except Exception:
        log.error("migrations_failed_at_startup", exc_info=True)

    # Same reasoning as the Mongo client above: fail fast, don't hang requests
    # (or readiness probes) for a default client timeout when a dependency is down.
    app.state.qdrant_client = AsyncQdrantClient(url=settings.qdrant_url, timeout=5)
    # redis-py's `from_url` lacks a return-type annotation upstream.
    app.state.redis_client = redis.from_url(  # type: ignore[no-untyped-call]
        settings.redis_url, socket_connect_timeout=5, socket_timeout=5
    )
    app.state.storage = _build_storage(settings)

    llm_client, llm_sdk_client = _build_llm_client(settings)
    app.state.llm_client = llm_client

    extractor, extractor_sdk_client = _build_extractor(settings)
    app.state.extractor = extractor

    # The job queue this process enqueues into (see routers/jobs.py and
    # deps.py) — the ARQ worker process is what actually runs the tasks,
    # sharing nothing with this process except Redis. Built lazily like
    # ``redis_client`` above (no eager ping) — unlike ``arq.connections.
    # create_pool``, which blocks startup retrying a connection for several
    # seconds and then raises if Redis isn't up yet.
    app.state.arq_pool = ArqRedis.from_url(settings.redis_url)

    log.info("startup_complete")
    try:
        yield
    finally:
        log.info("shutdown_begin")
        await mongo_client.close()
        await app.state.qdrant_client.close()
        await app.state.redis_client.aclose()
        await llm_sdk_client.close()
        await extractor_sdk_client.close()
        await app.state.arq_pool.aclose()
        log.info("shutdown_complete")


async def _check_mongo(request: Request) -> bool:
    return await mongo_ping(request.app.state.mongo_client)


async def _check_qdrant(request: Request) -> bool:
    try:
        await request.app.state.qdrant_client.get_collections()
    except Exception:  # noqa: BLE001 — health check: any failure means "not ready"
        return False
    return True


async def _check_redis(request: Request) -> bool:
    try:
        return bool(await request.app.state.redis_client.ping())
    except Exception:  # noqa: BLE001 — health check: any failure means "not ready"
        return False


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="LearnAI",
        version="0.2.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.cors_origins]
        or ["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or new_request_id()
        bind_request_id(request_id)
        start = time.monotonic()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        structlog.get_logger("learnai.access").info(
            "request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round((time.monotonic() - start) * 1000, 1),
        )
        return response

    register_exception_handlers(app)
    app.include_router(auth_router)
    app.include_router(profile_router)
    app.include_router(collections_router)
    app.include_router(jobs_router)
    app.include_router(materials_router)

    @app.get("/health/live", tags=["health"])
    async def health_live() -> dict[str, str]:
        """Process is up and serving. Does not touch any dependency."""
        return {"status": "ok"}

    @app.get("/health/ready", tags=["health"])
    async def health_ready(request: Request) -> JSONResponse:
        """Process is up AND every datastore it needs is reachable."""
        checks = {
            "mongo": await _check_mongo(request),
            "qdrant": await _check_qdrant(request),
            "redis": await _check_redis(request),
        }
        overall_ok = all(checks.values())
        return JSONResponse(
            status_code=200 if overall_ok else 503,
            content={"status": "ok" if overall_ok else "unavailable", "checks": checks},
        )

    return app


app = create_app()
