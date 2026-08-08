"""A minimal in-memory stand-in for a pymongo async collection/database.

Not a substitute for the real-Mongo integration tests in
``tests/integration/`` (those run against ``testcontainers`` in CI, with
real query semantics, real index enforcement, real concurrency). This fake
exists to unit-test ``ScopedRepository``'s *own* logic — does it inject
``owner_id`` where it should, does it reject callers who try to set it
themselves — deterministically and without a database, since that logic is
ours to get right and doesn't depend on anything MongoDB-specific.
"""

from __future__ import annotations

import copy
from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass, field
from typing import Any

from bson import ObjectId


@dataclass
class _InsertOneResult:
    inserted_id: ObjectId


@dataclass
class _UpdateResult:
    matched_count: int
    modified_count: int


@dataclass
class _DeleteResult:
    deleted_count: int


def _matches(doc: dict[str, Any], query: Mapping[str, Any]) -> bool:
    return all(doc.get(k) == v for k, v in query.items())


class FakeAsyncCursor:
    def __init__(self, docs: list[dict[str, Any]]) -> None:
        self._docs = docs

    def __aiter__(self) -> AsyncIterator[dict[str, Any]]:
        return self._iter()

    async def _iter(self) -> AsyncIterator[dict[str, Any]]:
        for doc in self._docs:
            yield copy.deepcopy(doc)


@dataclass
class FakeAsyncCollection:
    _docs: dict[str, dict[str, Any]] = field(default_factory=dict)

    async def find_one(self, query: Mapping[str, Any]) -> dict[str, Any] | None:
        for doc in self._docs.values():
            if _matches(doc, query):
                return copy.deepcopy(doc)
        return None

    def find(self, query: Mapping[str, Any], **_kwargs: Any) -> FakeAsyncCursor:
        return FakeAsyncCursor([d for d in self._docs.values() if _matches(d, query)])

    async def count_documents(self, query: Mapping[str, Any]) -> int:
        return sum(1 for d in self._docs.values() if _matches(d, query))

    async def insert_one(self, document: Mapping[str, Any]) -> _InsertOneResult:
        doc = dict(document)
        oid = doc.setdefault("_id", ObjectId())
        self._docs[str(oid)] = doc
        return _InsertOneResult(inserted_id=oid)

    async def update_one(
        self, query: Mapping[str, Any], update: Mapping[str, Any]
    ) -> _UpdateResult:
        for doc in self._docs.values():
            if _matches(doc, query):
                if "$set" in update:
                    doc.update(update["$set"])
                return _UpdateResult(matched_count=1, modified_count=1)
        return _UpdateResult(matched_count=0, modified_count=0)

    async def delete_one(self, query: Mapping[str, Any]) -> _DeleteResult:
        for key, doc in list(self._docs.items()):
            if _matches(doc, query):
                del self._docs[key]
                return _DeleteResult(deleted_count=1)
        return _DeleteResult(deleted_count=0)


class FakeAsyncDatabase:
    def __init__(self) -> None:
        self._collections: dict[str, FakeAsyncCollection] = {}

    def __getitem__(self, name: str) -> FakeAsyncCollection:
        return self._collections.setdefault(name, FakeAsyncCollection())
