"""Migrations and ScopedRepository against a real MongoDB.

Complements tests/unit/test_scoped_repository.py (same tenant-isolation
guarantees, verified against a fake) with the properties only a real
database can confirm: that create_index actually creates the indexes with
the right options, that re-running migrations is a genuine no-op against
real state, and that the scoping logic holds under MongoDB's actual query
engine, not just our own fake's.

Connects to `settings.mongodb_uri` — the same env var the app itself reads —
against a dedicated `learnai_test` database, dropped after each test. This
is deliberately *not* testcontainers-managed: CI's `test` job already
provisions Mongo via a `services:` container reachable at that URI, and a
local `docker compose up -d mongo` gives the same thing. Needing Docker
reachable *from inside the test process* would be a heavier, redundant
requirement on top of "Mongo is reachable somewhere."

Marked `integration` (see pyproject.toml) and excluded from the default
`pytest` invocation (`not live and not integration`) — run explicitly with
`pytest -m integration` once Mongo is up.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

import pytest
from bson import ObjectId
from pymongo import AsyncMongoClient
from pymongo.errors import DuplicateKeyError

from learnai.config import get_settings
from learnai.db.migrations import ALL_MIGRATIONS, apply_pending
from learnai.db.mongo import Database
from learnai.repositories.base import ScopedRepository

pytestmark = pytest.mark.integration


class _WidgetRepo(ScopedRepository[dict[str, Any]]):
    COLLECTION = "widgets"


@pytest.fixture
async def db() -> AsyncIterator[Database]:
    client: AsyncMongoClient[dict[str, Any]] = AsyncMongoClient(
        get_settings().mongodb_uri, serverSelectionTimeoutMS=5_000
    )
    database: Database = client["learnai_test"]
    yield database
    await client.drop_database("learnai_test")
    await client.close()


async def test_migrations_create_expected_indexes(db: Database) -> None:
    applied = await apply_pending(db, ALL_MIGRATIONS)
    assert applied == ["0001_initial_indexes"]

    users_indexes = await db["users"].index_information()
    assert users_indexes["google_sub_1"]["unique"] is True
    assert users_indexes["email_1"]["unique"] is True

    profile_indexes = await db["learning_profiles"].index_information()
    assert profile_indexes["owner_id_1"]["unique"] is True

    collections_indexes = await db["collections"].index_information()
    assert "owner_id_1_created_at_-1" in collections_indexes
    assert "parent_collection_id_1" in collections_indexes

    session_indexes = await db["sessions"].index_information()
    assert session_indexes["token_hash_1"]["unique"] is True
    assert session_indexes["expires_at_1"]["expireAfterSeconds"] == 0


async def test_migrations_are_idempotent(db: Database) -> None:
    first = await apply_pending(db, ALL_MIGRATIONS)
    second = await apply_pending(db, ALL_MIGRATIONS)

    assert first == ["0001_initial_indexes"]
    assert second == []  # already recorded applied — apply() not re-run


async def test_unique_index_actually_rejects_duplicates(db: Database) -> None:
    await apply_pending(db, ALL_MIGRATIONS)
    await db["users"].insert_one({"google_sub": "sub-123", "email": "a@example.com"})

    with pytest.raises(DuplicateKeyError):
        await db["users"].insert_one({"google_sub": "sub-123", "email": "b@example.com"})


async def test_tenant_isolation_holds_against_real_query_engine(db: Database) -> None:
    owner_a, owner_b = ObjectId(), ObjectId()
    repo_a = _WidgetRepo(db, owner_a)
    repo_b = _WidgetRepo(db, owner_b)

    widget_id = await repo_a.insert_one({"payload": "only-a-should-see-this-value"})

    assert await repo_b.find_one({"_id": widget_id}) is None
    found = await repo_a.find_one({"_id": widget_id})
    assert found is not None
    assert found["payload"] == "only-a-should-see-this-value"

    update_result = await repo_b.update_one({"_id": widget_id}, {"$set": {"payload": "hijacked"}})
    assert update_result.matched_count == 0

    still_a = await repo_a.find_one({"_id": widget_id})
    assert still_a is not None
    assert still_a["payload"] == "only-a-should-see-this-value"


async def test_concurrent_appends_produce_no_lost_updates(db: Database) -> None:
    """The exact failure mode the old S3-blob chat history had: N concurrent
    writers, each doing a naive read-modify-write, silently lose updates.
    ScopedRepository.insert_one is a single atomic insert per call, so N
    concurrent inserts must produce exactly N documents, no gaps, no clobbers."""
    owner = ObjectId()
    repo = _WidgetRepo(db, owner)

    await asyncio.gather(*(repo.insert_one({"seq": i}) for i in range(20)))

    seqs = sorted([doc["seq"] async for doc in repo.find({})])
    assert seqs == list(range(20))
