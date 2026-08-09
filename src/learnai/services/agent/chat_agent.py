"""The chat agent — a ReAct loop over the collection's materials via
``services/agent/tools.py``'s owner-scoped tools, per the modernization
plan's "Chat becomes a ReAct agent" design.

Replaces the old design's single-shot prompt that stuffed three fixed
blobs into context and searched the knowledge base with the *document*
as the query (``extracted_text[:2000]``) on every message. Here the model
decides what to search for and reads the tree first to scope it — the
retrieval step PageIndex spends 30s of sequential reasoning on, done once
against a tree that's already cheap to hold in context.

Persists the user's message and the assistant's reply as separate
``chat_messages`` documents (see ``repositories/conversations.py``,
``repositories/chat_messages.py``) rather than the old design's whole-
conversation JSON blob GET-modified-PUT.
"""

from __future__ import annotations

import json
from typing import Any

from bson import ObjectId

from learnai.config import LLMTask, Settings
from learnai.repositories.artifacts import ArtifactRepository
from learnai.repositories.chat_messages import ChatMessageRepository
from learnai.repositories.conversations import ConversationRepository
from learnai.repositories.learning_profiles import LearningProfileRepository
from learnai.repositories.materials import MaterialRepository
from learnai.repositories.sections import SectionRepository
from learnai.schemas.chat import ChatCitation
from learnai.services.agent.tools import build_tools
from learnai.services.extraction.base import DocumentExtractor
from learnai.services.llm.client import AgentToolCall, LLMClient
from learnai.services.llm.prompts import render
from learnai.services.retrieval.embedder import Embedder
from learnai.services.retrieval.vector_store import VectorStore
from learnai.services.storage.base import StorageBackend

# Two guards the plan calls out for the agent loop: this bound on tool-use
# iterations, and (inside AnthropicLLMClient.agent) explicit pause_turn
# handling — the Python tool_runner does not auto-resume on its own.
MAX_AGENT_ITERATIONS = 8

_NO_PROFILE_DESCRIPTION = "No stated learning-style preference yet."


async def send_message(
    *,
    owner_id: ObjectId,
    collection: dict[str, Any],
    message: str,
    conversations: ConversationRepository,
    chat_messages: ChatMessageRepository,
    learning_profiles: LearningProfileRepository,
    materials: MaterialRepository,
    sections: SectionRepository,
    storage: StorageBackend,
    extractor: DocumentExtractor,
    embedder: Embedder,
    vector_store: VectorStore,
    settings: Settings,
    artifacts: ArtifactRepository,
    llm: LLMClient,
) -> dict[str, Any]:
    """Appends the user's message, runs the agent, appends and returns the
    assistant's reply — the persisted ``chat_messages`` document, citations
    included."""
    conversation = await conversations.get_or_create(collection["_id"])

    history = await chat_messages.list_for_conversation(conversation["_id"])
    user_seq = await conversations.next_seq(conversation["_id"])
    user_message = await chat_messages.append(
        conversation_id=conversation["_id"], seq=user_seq, role="user", content=message
    )

    profile = await learning_profiles.get()
    profile_description = profile["description"] if profile is not None else _NO_PROFILE_DESCRIPTION

    tools = build_tools(
        owner_id=owner_id,
        collection=collection,
        materials=materials,
        sections=sections,
        storage=storage,
        extractor=extractor,
        embedder=embedder,
        vector_store=vector_store,
        settings=settings,
        learning_profiles=learning_profiles,
        artifacts=artifacts,
        llm=llm,
    )

    conversation_turns = [
        {"role": doc["role"], "content": doc["content"]} for doc in [*history, user_message]
    ]

    result = await llm.agent(
        task=LLMTask.chat,
        system=render("chat_system.j2", learning_profile=profile_description),
        messages=conversation_turns,
        tools=tools,
        max_iterations=MAX_AGENT_ITERATIONS,
    )

    assistant_seq = await conversations.next_seq(conversation["_id"])
    return await chat_messages.append(
        conversation_id=conversation["_id"],
        seq=assistant_seq,
        role="assistant",
        content=result.text,
        citations=_citations_from_tool_calls(result.tool_calls),
    )


def _citations_from_tool_calls(tool_calls: list[AgentToolCall]) -> list[ChatCitation]:
    """Citations come straight from the agent's own search_materials
    calls — real provenance for whatever it actually looked at, not a
    guess reconstructed after the fact. Deduped by (material_id, node_id)
    since the same passage can surface across more than one call."""
    seen: set[tuple[str, str]] = set()
    citations: list[ChatCitation] = []
    for call in tool_calls:
        if call.tool_name != "search_materials":
            continue
        try:
            hits = json.loads(call.result)
        except json.JSONDecodeError:
            continue
        for hit in hits:
            key = (hit["material_id"], hit["node_id"])
            if key in seen:
                continue
            seen.add(key)
            citations.append(
                ChatCitation(
                    material_id=hit["material_id"],
                    node_id=hit["node_id"],
                    title=hit["title"],
                    page=hit["page"],
                )
            )
    return citations
