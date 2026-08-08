"""FastAPI dependency-injection providers.

This is the one place a ``Protocol`` (``StorageBackend``, ``LLMClient``,
``VectorStore``, ...) gets bound to a concrete implementation. Everything here
reads pre-built singletons off ``request.app.state`` — they're constructed
once in ``main.py``'s ``lifespan``, not per-request and not at import time.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Cookie, Depends, Request

from learnai.config import Settings, get_settings
from learnai.db.mongo import Database
from learnai.errors import Unauthenticated
from learnai.repositories.collections import CollectionRepository
from learnai.repositories.learning_profiles import LearningProfileRepository
from learnai.repositories.sessions import SessionRepository
from learnai.repositories.users import UserRepository
from learnai.services.auth.session import SessionService
from learnai.services.storage.base import StorageBackend

# Cookie names, shared between the auth router (which sets/clears them) and
# get_current_user (which reads the access cookie). Not settings — these are
# an internal implementation detail, never configured per-deployment.
ACCESS_TOKEN_COOKIE = "learnai_access"  # noqa: S105 - a cookie name, not a credential
REFRESH_TOKEN_COOKIE = "learnai_refresh"  # noqa: S105 - a cookie name, not a credential


def get_db(request: Request) -> Database:
    db: Database = request.app.state.mongo_db
    return db


def get_storage(request: Request) -> StorageBackend:
    storage: StorageBackend = request.app.state.storage
    return storage


SettingsDep = Annotated[Settings, Depends(get_settings)]
StorageDep = Annotated[StorageBackend, Depends(get_storage)]

# Internal building block for repository/service providers below. Routers
# should depend on a repository/service type, never on DbDep directly — that
# would bypass the routers -> services -> repositories -> db layering.
DbDep = Annotated[Database, Depends(get_db)]


def get_user_repo(db: DbDep) -> UserRepository:
    return UserRepository(db)


UserRepoDep = Annotated[UserRepository, Depends(get_user_repo)]


def get_session_service(settings: SettingsDep, db: DbDep) -> SessionService:
    return SessionService(
        SessionRepository(db),
        session_secret=settings.session_secret.get_secret_value(),
        access_token_ttl_seconds=settings.access_token_ttl_seconds,
        refresh_token_ttl_seconds=settings.refresh_token_ttl_seconds,
    )


SessionServiceDep = Annotated[SessionService, Depends(get_session_service)]


async def get_current_user(
    db: DbDep,
    session_service: SessionServiceDep,
    access_token: Annotated[str | None, Cookie(alias=ACCESS_TOKEN_COOKIE)] = None,
) -> dict[str, Any]:
    """The authenticated user's document, or ``Unauthenticated`` (401).

    Every repository/service provider that needs owner scoping (below)
    depends on this rather than reading the cookie itself — one place
    verifies the access token, everything else just trusts the result.
    """
    if access_token is None:
        raise Unauthenticated("not authenticated")
    claims = session_service.verify_access_token(access_token)
    user = await UserRepository(db).find_by_id(claims.user_id)
    if user is None:
        raise Unauthenticated("user no longer exists")
    return user


CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]


def get_collection_repo(user: CurrentUser, db: DbDep) -> CollectionRepository:
    return CollectionRepository(db, user["_id"])


CollectionRepoDep = Annotated[CollectionRepository, Depends(get_collection_repo)]


def get_learning_profile_repo(user: CurrentUser, db: DbDep) -> LearningProfileRepository:
    return LearningProfileRepository(db, user["_id"])


LearningProfileRepoDep = Annotated[LearningProfileRepository, Depends(get_learning_profile_repo)]
