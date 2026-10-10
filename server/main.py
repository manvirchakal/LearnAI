"""
LearnAI FastAPI application factory.

Layering:
    routes/   HTTP only: validation, status codes, response models
    agents/   LangGraph workflows for anything multi-step or LLM-driven
    services/ single-purpose domain operations (storage, PDFs, RAG, media)
    utils/    pure helpers (prompts, TOC normalization, code/diagram cleanup)
    core/     config, storage backend, vector store, LLM client

The MCP server (mcp_server/) exposes the same local services as tools and is
mounted at /mcp (streamable HTTP).
"""
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import settings
from mcp_server.server import server as mcp_server
from routes.accessibility import router as accessibility_router
from routes.books import router as books_router
from routes.collections import router as collections_router
from routes.health import router as health_router
from routes.media import router as media_router
from routes.notes import router as notes_router
from routes.profile import router as profile_router

logging.basicConfig(
    level=settings.LOG_LEVEL.upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
for noisy in ("botocore", "boto3", "httpx", "openai"):
    logging.getLogger(noisy).setLevel(logging.WARNING)


def create_app() -> FastAPI:
    mcp_app = mcp_server.http_app(path="/")
    app = FastAPI(title="LearnAI API", version="2.0.0", lifespan=mcp_app.lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024

    @app.middleware("http")
    async def limit_upload_size(request: Request, call_next):
        length = request.headers.get("content-length")
        if length and length.isdigit() and int(length) > max_bytes:
            return JSONResponse({"detail": f"Upload exceeds {settings.MAX_UPLOAD_MB} MB"}, status_code=413)
        return await call_next(request)

    for router in (health_router, profile_router, books_router, collections_router, media_router,
                   notes_router, accessibility_router):
        app.include_router(router)

    app.mount("/mcp", mcp_app)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=True)
