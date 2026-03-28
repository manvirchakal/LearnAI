"""
LearnAI FastAPI application factory.
All business logic lives in routes/, services/, agents/, utils/, core/.
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from routes.profile import router as profile_router
from routes.textbooks import router as textbooks_router
from routes.content import router as content_router
from routes.chat import router as chat_router
from routes.media import router as media_router
from routes.collections import router as collections_router
from routes.accessibility import router as accessibility_router
from routes.notes import router as notes_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logging.getLogger("botocore").setLevel(logging.WARNING)
logging.getLogger("boto3").setLevel(logging.WARNING)


def create_app() -> FastAPI:
    app = FastAPI(title="LearnAI API", version="2.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(profile_router)
    app.include_router(textbooks_router)
    app.include_router(content_router)
    app.include_router(chat_router)
    app.include_router(media_router)
    app.include_router(collections_router)
    app.include_router(accessibility_router)
    app.include_router(notes_router)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=True)
