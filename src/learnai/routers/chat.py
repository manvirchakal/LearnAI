"""Chat API — the ReAct agent (``services/agent/chat_agent.py``) over one
collection's materials. Shares the ``/api/v1/collections`` prefix with
``routers/collections.py`` and ``routers/generation.py`` (a separate
router file per the target module layout, same path space).
"""

from __future__ import annotations

from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter

from learnai.deps import (
    ArtifactRepoDep,
    ChatMessageRepoDep,
    CollectionRepoDep,
    ConversationRepoDep,
    CurrentUser,
    EmbedderDep,
    ExtractorDep,
    LearningProfileRepoDep,
    LLMClientDep,
    MaterialRepoDep,
    SectionRepoDep,
    SettingsDep,
    StorageDep,
    VectorStoreDep,
)
from learnai.errors import ValidationError
from learnai.schemas.chat import ChatCitation, ChatMessageOut, ChatRequest
from learnai.services.agent.chat_agent import send_message

router = APIRouter(prefix="/api/v1/collections", tags=["chat"])


def _object_id(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except InvalidId as exc:
        raise ValidationError(f"invalid id: {value!r}") from exc


def _message_out(doc: dict[str, Any]) -> ChatMessageOut:
    return ChatMessageOut(
        id=str(doc["_id"]),
        seq=doc["seq"],
        role=doc["role"],
        content=doc["content"],
        citations=[ChatCitation.model_validate(c) for c in doc.get("citations", [])],
        created_at=doc["created_at"],
    )


@router.get("/{collection_id}/chat", response_model=list[ChatMessageOut])
async def get_chat_history(
    collection_id: str,
    collections: CollectionRepoDep,
    conversations: ConversationRepoDep,
    chat_messages: ChatMessageRepoDep,
) -> list[ChatMessageOut]:
    collection = await collections.get(_object_id(collection_id))
    conversation = await conversations.get_or_create(collection["_id"])
    messages = await chat_messages.list_for_conversation(conversation["_id"])
    return [_message_out(doc) for doc in messages]


@router.post("/{collection_id}/chat", response_model=ChatMessageOut)
async def post_chat_message(
    collection_id: str,
    body: ChatRequest,
    collections: CollectionRepoDep,
    conversations: ConversationRepoDep,
    chat_messages: ChatMessageRepoDep,
    learning_profiles: LearningProfileRepoDep,
    materials: MaterialRepoDep,
    sections: SectionRepoDep,
    storage: StorageDep,
    extractor: ExtractorDep,
    embedder: EmbedderDep,
    vector_store: VectorStoreDep,
    settings: SettingsDep,
    artifacts: ArtifactRepoDep,
    llm: LLMClientDep,
    user: CurrentUser,
) -> ChatMessageOut:
    collection = await collections.get(_object_id(collection_id))
    reply = await send_message(
        owner_id=user["_id"],
        collection=collection,
        message=body.message,
        conversations=conversations,
        chat_messages=chat_messages,
        learning_profiles=learning_profiles,
        materials=materials,
        sections=sections,
        storage=storage,
        extractor=extractor,
        embedder=embedder,
        vector_store=vector_store,
        settings=settings,
        artifacts=artifacts,
        llm=llm,
    )
    return _message_out(reply)
