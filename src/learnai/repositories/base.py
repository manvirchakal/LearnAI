"""``ScopedRepository`` — the enforcement point for multi-tenancy.

The old design isolated users by S3 key prefix plus eight scattered
``if user_id != current_user: 403`` checks scattered across handlers — an
approach that is fail-*open* by default: forget one check anywhere and that
endpoint leaks another user's data. ``/api/chat`` did exactly that (it read
``userId`` from the request body and fetched that user's extracted text,
narratives, and chat history with no ownership check at all).

Here, ``owner_id`` is bound once, at construction, from the authenticated
user (see ``deps.py`` — a repository is only ever built from
``Depends(get_current_user)``), and injected into every query the repository
runs. There is no method on this class — or any subclass — that can reach
another owner's documents. A missing document and someone else's document
produce the identical result: ``None`` / zero matched, which routers turn
into a 404, not a 403. No existence oracle.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Generic, TypeVar

from bson import ObjectId
from pymongo.asynchronous.cursor import AsyncCursor
from pymongo.results import DeleteResult, InsertOneResult, UpdateResult

from learnai.db.mongo import Database

Document = dict[str, Any]
T = TypeVar("T", bound=Document)


class ScopeViolation(RuntimeError):
    """A repository method was called in a way that would have bypassed
    owner scoping. Always a programming error, never a runtime/user-facing
    condition — if this fires, fix the call site, don't catch it."""


class ScopedRepository(Generic[T]):
    #: Mongo collection name. Set by subclasses.
    COLLECTION: str

    def __init__(self, db: Database, owner_id: ObjectId) -> None:
        self._db = db
        self._collection = db[self.COLLECTION]
        self._owner_id = owner_id

    @property
    def owner_id(self) -> ObjectId:
        return self._owner_id

    def _scope(self, query: Mapping[str, Any]) -> dict[str, Any]:
        if "owner_id" in query:
            raise ScopeViolation(
                "owner_id is injected by ScopedRepository, never passed explicitly"
            )
        return {**query, "owner_id": self._owner_id}

    async def find_one(self, query: Mapping[str, Any]) -> T | None:
        result = await self._collection.find_one(self._scope(query))
        return result  # type: ignore[return-value]

    def find(self, query: Mapping[str, Any], **kwargs: Any) -> AsyncCursor[T]:
        return self._collection.find(self._scope(query), **kwargs)  # type: ignore[return-value]

    async def count(self, query: Mapping[str, Any]) -> int:
        return await self._collection.count_documents(self._scope(query))

    async def insert_one(self, document: Mapping[str, Any]) -> ObjectId:
        if "owner_id" in document:
            raise ScopeViolation("owner_id is injected by ScopedRepository, never set explicitly")
        result: InsertOneResult = await self._collection.insert_one(
            {**document, "owner_id": self._owner_id}
        )
        inserted_id: ObjectId = result.inserted_id
        return inserted_id

    async def update_one(
        self, query: Mapping[str, Any], update: Mapping[str, Any], *, upsert: bool = False
    ) -> UpdateResult:
        # Safe with upsert=True: the query always includes {"owner_id": self._owner_id}
        # (via _scope), and Mongo builds an upserted document from the query's
        # equality conditions — so a newly-created document is correctly owned
        # without any extra work here.
        return await self._collection.update_one(self._scope(query), dict(update), upsert=upsert)

    async def delete_one(self, query: Mapping[str, Any]) -> DeleteResult:
        return await self._collection.delete_one(self._scope(query))
