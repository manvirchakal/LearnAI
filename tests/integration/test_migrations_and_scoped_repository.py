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
from learnai.repositories.chat_messages import ChatMessageRepository
from learnai.repositories.collections import CollectionRepository
from learnai.repositories.conversations import ConversationRepository
from learnai.repositories.users import UserRepository

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
    assert applied == [
        "0001_initial_indexes",
        "0002_materials_and_sections_indexes",
        "0003_jobs_indexes",
        "0004_artifacts_indexes",
        "0005_chat_indexes",
        "0006_translations_indexes",
    ]

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

    materials_indexes = await db["materials"].index_information()
    assert "owner_id_1_created_at_-1" in materials_indexes

    section_indexes = await db["sections"].index_information()
    assert section_indexes["owner_id_1_material_id_1_node_id_1"]["unique"] is True

    job_indexes = await db["jobs"].index_information()
    assert "owner_id_1_created_at_-1" in job_indexes

    artifact_indexes = await db["artifacts"].index_information()
    assert artifact_indexes["owner_id_1_collection_id_1_kind_1_fingerprint_1"]["unique"] is True

    conversation_indexes = await db["conversations"].index_information()
    assert conversation_indexes["owner_id_1_collection_id_1"]["unique"] is True

    chat_message_indexes = await db["chat_messages"].index_information()
    assert chat_message_indexes["owner_id_1_conversation_id_1_seq_1"]["unique"] is True

    translation_indexes = await db["translations"].index_information()
    assert translation_indexes["owner_id_1_text_hash_1_target_language_1"]["unique"] is True


async def test_migrations_are_idempotent(db: Database) -> None:
    first = await apply_pending(db, ALL_MIGRATIONS)
    second = await apply_pending(db, ALL_MIGRATIONS)

    assert first == [
        "0001_initial_indexes",
        "0002_materials_and_sections_indexes",
        "0003_jobs_indexes",
        "0004_artifacts_indexes",
        "0005_chat_indexes",
        "0006_translations_indexes",
    ]
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


async def test_collection_list_all_is_newest_first_against_real_index(db: Database) -> None:
    """The fake collection doesn't implement sort at all, so this — the
    {owner_id, created_at} index actually producing newest-first order —
    can only be verified here."""
    await apply_pending(db, ALL_MIGRATIONS)
    repo = CollectionRepository(db, ObjectId())

    # Small gaps guarantee strictly increasing created_at — without them,
    # three inserts this close together could tie at microsecond resolution
    # and make the asserted order flaky.
    first_id = await repo.create(name="first", kind="manual")
    await asyncio.sleep(0.01)
    second_id = await repo.create(name="second", kind="manual")
    await asyncio.sleep(0.01)
    third_id = await repo.create(name="third", kind="manual")

    ids_in_order = [doc["_id"] for doc in await repo.list_all()]
    assert ids_in_order == [third_id, second_id, first_id]


async def test_user_upsert_from_google_is_idempotent_against_real_mongo(db: Database) -> None:
    repo = UserRepository(db)

    first = await repo.upsert_from_google(
        google_sub="sub-real-1",
        email="a@example.com",
        email_verified=True,
        name="Ada",
        picture=None,
    )
    second = await repo.upsert_from_google(
        google_sub="sub-real-1",
        email="a@example.com",
        email_verified=True,
        name="Ada Lovelace",
        picture="https://example.com/pic.jpg",
    )

    assert second["_id"] == first["_id"]
    assert second["created_at"] == first["created_at"]
    assert second["name"] == "Ada Lovelace"


async def test_concurrent_chat_seq_allocation_has_no_gaps_or_dupes(db: Database) -> None:
    """The exact property the old S3 chat-history blob lacked: N concurrent
    senders each get a distinct, gapless seq, and the unique
    (owner_id, conversation_id, seq) index makes a collision impossible to
    persist even if the counter's atomicity were ever broken."""
    await apply_pending(db, ALL_MIGRATIONS)
    owner = ObjectId()
    conversations = ConversationRepository(db, owner)
    messages = ChatMessageRepository(db, owner)
    conversation = await conversations.get_or_create(ObjectId())

    async def send(i: int) -> None:
        seq = await conversations.next_seq(conversation["_id"])
        await messages.append(
            conversation_id=conversation["_id"], seq=seq, role="user", content=f"message {i}"
        )

    await asyncio.gather(*(send(i) for i in range(20)))

    stored = await messages.list_for_conversation(conversation["_id"])
    assert sorted(doc["seq"] for doc in stored) == list(range(1, 21))
