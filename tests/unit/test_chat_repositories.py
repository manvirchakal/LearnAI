from __future__ import annotations

import pytest
from bson import ObjectId

from learnai.errors import NotFound
from learnai.repositories.chat_messages import ChatMessageRepository
from learnai.repositories.conversations import ConversationRepository
from learnai.schemas.chat import ChatRole
from tests.fakes.mongo import FakeAsyncDatabase


@pytest.fixture
def db() -> FakeAsyncDatabase:
    return FakeAsyncDatabase()


async def test_get_or_create_is_idempotent_per_collection(db: FakeAsyncDatabase) -> None:
    repo = ConversationRepository(db, ObjectId())  # type: ignore[arg-type]
    collection_id = ObjectId()

    first = await repo.get_or_create(collection_id)
    second = await repo.get_or_create(collection_id)

    assert first["_id"] == second["_id"]


async def test_get_or_create_is_scoped_per_owner(db: FakeAsyncDatabase) -> None:
    owner_a, owner_b = ObjectId(), ObjectId()
    collection_id = ObjectId()

    conv_a = await ConversationRepository(db, owner_a).get_or_create(collection_id)  # type: ignore[arg-type]
    conv_b = await ConversationRepository(db, owner_b).get_or_create(collection_id)  # type: ignore[arg-type]

    assert conv_a["_id"] != conv_b["_id"]


async def test_next_seq_increments_from_one(db: FakeAsyncDatabase) -> None:
    repo = ConversationRepository(db, ObjectId())  # type: ignore[arg-type]
    conversation = await repo.get_or_create(ObjectId())

    assert await repo.next_seq(conversation["_id"]) == 1
    assert await repo.next_seq(conversation["_id"]) == 2
    assert await repo.next_seq(conversation["_id"]) == 3


async def test_next_seq_on_missing_conversation_raises_not_found(db: FakeAsyncDatabase) -> None:
    repo = ConversationRepository(db, ObjectId())  # type: ignore[arg-type]
    with pytest.raises(NotFound):
        await repo.next_seq(ObjectId())


async def test_append_then_list_is_seq_ordered(db: FakeAsyncDatabase) -> None:
    owner = ObjectId()
    conversations = ConversationRepository(db, owner)  # type: ignore[arg-type]
    messages = ChatMessageRepository(db, owner)  # type: ignore[arg-type]
    conversation = await conversations.get_or_create(ObjectId())

    turns: list[tuple[ChatRole, str]] = [
        ("user", "hi"),
        ("assistant", "hello"),
        ("user", "thanks"),
    ]
    for role, content in turns:
        seq = await conversations.next_seq(conversation["_id"])
        await messages.append(
            conversation_id=conversation["_id"], seq=seq, role=role, content=content
        )

    listed = await messages.list_for_conversation(conversation["_id"])
    assert [m["content"] for m in listed] == ["hi", "hello", "thanks"]
    assert [m["seq"] for m in listed] == [1, 2, 3]


async def test_messages_are_owner_scoped(db: FakeAsyncDatabase) -> None:
    owner_a, owner_b = ObjectId(), ObjectId()
    conversation = await ConversationRepository(db, owner_a).get_or_create(ObjectId())  # type: ignore[arg-type]
    messages_a = ChatMessageRepository(db, owner_a)  # type: ignore[arg-type]
    messages_b = ChatMessageRepository(db, owner_b)  # type: ignore[arg-type]

    await messages_a.append(
        conversation_id=conversation["_id"], seq=1, role="user", content="secret"
    )

    assert await messages_b.list_for_conversation(conversation["_id"]) == []
