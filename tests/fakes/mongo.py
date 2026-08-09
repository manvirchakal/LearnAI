"""A minimal in-memory stand-in for a pymongo async collection/database.

Not a substitute for the real-Mongo integration tests in
``tests/integration/`` (those connect to a real MongoDB — see that module's
docstring — with real query semantics, real index enforcement, real
concurrency). This fake exists to unit-test repository *logic*
deterministically and without a database: does ``ScopedRepository`` inject
``owner_id`` where it should, does an upsert seed the right fields, does
``created_at`` survive a retake. That's ours to get right and doesn't
depend on anything MongoDB-specific.
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


def _apply_set(doc: dict[str, Any], update: Mapping[str, Any]) -> None:
    if "$set" in update:
        doc.update(update["$set"])
    if "$inc" in update:
        for key, delta in update["$inc"].items():
            doc[key] = doc.get(key, 0) + delta


def _seed_from_upsert(query: Mapping[str, Any], update: Mapping[str, Any]) -> dict[str, Any]:
    # Real MongoDB seeds a new document from the query's top-level equality
    # fields plus the update's $set/$setOnInsert — mirrored here so a
    # fake-backed upsert test exercises the same shape a real one would.
    new_doc: dict[str, Any] = {k: v for k, v in query.items() if not k.startswith("$")}
    new_doc.update(update.get("$set", {}))
    new_doc.update(update.get("$setOnInsert", {}))
    for key, delta in update.get("$inc", {}).items():
        new_doc[key] = new_doc.get(key, 0) + delta
    return new_doc


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
        self, query: Mapping[str, Any], update: Mapping[str, Any], upsert: bool = False
    ) -> _UpdateResult:
        for doc in self._docs.values():
            if _matches(doc, query):
                _apply_set(doc, update)
                return _UpdateResult(matched_count=1, modified_count=1)
        if upsert:
            new_doc = _seed_from_upsert(query, update)
            oid = new_doc.setdefault("_id", ObjectId())
            self._docs[str(oid)] = new_doc
        return _UpdateResult(matched_count=0, modified_count=0)

    async def update_many(
        self, query: Mapping[str, Any], update: Mapping[str, Any], upsert: bool = False
    ) -> _UpdateResult:
        matched = [doc for doc in self._docs.values() if _matches(doc, query)]
        for doc in matched:
            _apply_set(doc, update)
        if not matched and upsert:
            new_doc = _seed_from_upsert(query, update)
            oid = new_doc.setdefault("_id", ObjectId())
            self._docs[str(oid)] = new_doc
        return _UpdateResult(matched_count=len(matched), modified_count=len(matched))

    async def find_one_and_update(
        self,
        query: Mapping[str, Any],
        update: Mapping[str, Any],
        upsert: bool = False,
        return_document: bool = False,
    ) -> dict[str, Any] | None:
        for doc in self._docs.values():
            if _matches(doc, query):
                before = copy.deepcopy(doc)
                _apply_set(doc, update)
                return copy.deepcopy(doc) if return_document else before
        if upsert:
            new_doc = _seed_from_upsert(query, update)
            oid = new_doc.setdefault("_id", ObjectId())
            self._docs[str(oid)] = new_doc
            return copy.deepcopy(new_doc) if return_document else None
        return None

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
