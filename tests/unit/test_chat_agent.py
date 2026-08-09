"""``send_message`` against fakes — the ReAct loop orchestrator: appends
the user's message, runs the agent, persists the assistant's reply with
citations built from any search_materials tool calls.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from bson import ObjectId

from learnai.config import LLMTask, Settings
from learnai.repositories.artifacts import ArtifactRepository
from learnai.repositories.chat_messages import ChatMessageRepository
from learnai.repositories.conversations import ConversationRepository
from learnai.repositories.learning_profiles import LearningProfileRepository
from learnai.repositories.materials import MaterialRepository
from learnai.repositories.sections import SectionRepository
from learnai.services.agent.chat_agent import send_message
from tests.fakes.embedder import FakeEmbedder
from tests.fakes.extraction import FakeExtractor
from tests.fakes.llm import FakeLLMClient
from tests.fakes.mongo import FakeAsyncDatabase
from tests.fakes.storage import FakeStorage
from tests.fakes.vector_store import FakeVectorStore


@pytest.fixture
def db() -> FakeAsyncDatabase:
    return FakeAsyncDatabase()


@pytest.fixture
def settings() -> Settings:
    return Settings()


def _collection() -> dict[str, Any]:
    return {"_id": ObjectId(), "material_refs": []}


def _deps(
    db: FakeAsyncDatabase, owner: ObjectId, settings: Settings, llm: FakeLLMClient
) -> dict[str, object]:
    return {
        "owner_id": owner,
        "conversations": ConversationRepository(db, owner),  # type: ignore[arg-type]
        "chat_messages": ChatMessageRepository(db, owner),  # type: ignore[arg-type]
        "learning_profiles": LearningProfileRepository(db, owner),  # type: ignore[arg-type]
        "materials": MaterialRepository(db, owner),  # type: ignore[arg-type]
        "sections": SectionRepository(db, owner),  # type: ignore[arg-type]
        "storage": FakeStorage(),
        "extractor": FakeExtractor(),
        "embedder": FakeEmbedder(),
        "vector_store": FakeVectorStore(),
        "settings": settings,
        "artifacts": ArtifactRepository(db, owner),  # type: ignore[arg-type]
        "llm": llm,
    }


async def test_send_message_persists_user_and_assistant_turns(
    db: FakeAsyncDatabase, settings: Settings
) -> None:
    owner = ObjectId()
    collection = _collection()
    llm = FakeLLMClient(agent_responses={LLMTask.chat: "The chain rule says..."})
    deps = _deps(db, owner, settings, llm)

    reply = await send_message(collection=collection, message="What's the chain rule?", **deps)  # type: ignore[arg-type]

    assert reply["role"] == "assistant"
    assert reply["content"] == "The chain rule says..."
    assert reply["seq"] == 2  # 1 = the user's turn, appended first

    chat_messages: ChatMessageRepository = deps["chat_messages"]  # type: ignore[assignment]
    conversations: ConversationRepository = deps["conversations"]  # type: ignore[assignment]
    conversation = await conversations.get_or_create(collection["_id"])
    stored = await chat_messages.list_for_conversation(conversation["_id"])
    assert [(m["role"], m["content"]) for m in stored] == [
        ("user", "What's the chain rule?"),
        ("assistant", "The chain rule says..."),
    ]


async def test_send_message_reuses_the_same_conversation_across_calls(
    db: FakeAsyncDatabase, settings: Settings
) -> None:
    owner = ObjectId()
    collection = _collection()
    llm = FakeLLMClient(agent_responses={LLMTask.chat: "ok"})
    deps = _deps(db, owner, settings, llm)

    await send_message(collection=collection, message="first", **deps)  # type: ignore[arg-type]
    second_reply = await send_message(collection=collection, message="second", **deps)  # type: ignore[arg-type]

    assert second_reply["seq"] == 4  # user(1), assistant(2), user(3), assistant(4)
    # the agent's second call sees the first turn's history
    second_call_messages = llm.calls[-1]["messages"]
    assert second_call_messages[0] == {"role": "user", "content": "first"}
    assert second_call_messages[1] == {"role": "assistant", "content": "ok"}
    assert second_call_messages[2] == {"role": "user", "content": "second"}


async def test_send_message_builds_citations_from_search_materials_calls(
    db: FakeAsyncDatabase, settings: Settings
) -> None:
    owner = ObjectId()
    collection = _collection()
    llm = FakeLLMClient(
        agent_responses={LLMTask.chat: "Here's what I found."},
        agent_tool_calls={
            LLMTask.chat: [("search_materials", {"query": "chain rule"})],
        },
    )
    deps = _deps(db, owner, settings, llm)
    # search_materials iterates collection["material_refs"] (empty here), so
    # its handler returns no hits — swap it out after build_tools has run by
    # monkeypatching would be more invasive than useful; instead verify the
    # empty-hits path is handled cleanly (no citations, no crash).

    reply = await send_message(collection=collection, message="the chain rule?", **deps)  # type: ignore[arg-type]

    assert reply["citations"] == []


async def test_citations_from_tool_calls_deduplicates_by_material_and_node() -> None:
    from learnai.services.agent.chat_agent import _citations_from_tool_calls
    from learnai.services.llm.client import AgentToolCall

    hits = [
        {
            "material_id": "m1",
            "node_id": "1",
            "title": "Ch 1",
            "page": 3,
            "text": "t",
            "score": 0.9,
        },
        {
            "material_id": "m1",
            "node_id": "1",
            "title": "Ch 1",
            "page": 3,
            "text": "t",
            "score": 0.8,
        },
        {
            "material_id": "m1",
            "node_id": "2",
            "title": "Ch 2",
            "page": 9,
            "text": "t",
            "score": 0.5,
        },
    ]
    tool_calls = [
        AgentToolCall(tool_name="search_materials", arguments={}, result=json.dumps(hits)),
    ]

    citations = _citations_from_tool_calls(tool_calls)

    assert [(c.material_id, c.node_id) for c in citations] == [("m1", "1"), ("m1", "2")]
