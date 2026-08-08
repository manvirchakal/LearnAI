"""FastAPI dependency-injection providers.

This is the one place a ``Protocol`` (``StorageBackend``, ``LLMClient``,
``VectorStore``, ...) gets bound to a concrete implementation. Everything here
reads pre-built singletons off ``request.app.state`` — they're constructed
once in ``main.py``'s ``lifespan``, not per-request and not at import time.

Phase 0 only wires the primitives (settings, the Mongo database handle).
Repository, storage, and LLM-client providers land in Phases 1-2 as those
services are built; this module is where they'll be added.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from learnai.config import Settings, get_settings
from learnai.db.mongo import Database


def get_db(request: Request) -> Database:
    db: Database = request.app.state.mongo_db
    return db


SettingsDep = Annotated[Settings, Depends(get_settings)]

# Internal building block for repository providers (Phase 1), e.g.
#   def get_material_repo(user: CurrentUser, db: DbDep) -> MaterialRepo: ...
# Routers should depend on a repository/service type, never on DbDep directly —
# that would bypass the routers -> services -> repositories -> db layering.
DbDep = Annotated[Database, Depends(get_db)]
