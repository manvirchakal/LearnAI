"""Chat request/response shapes for ``routers/chat.py``.

Citations here are a distinct, smaller shape from ``documents.Citation``
(that one carries ``cited_text``/page range from PDF extraction citations).
A chat citation is a pointer back into the reader — built straight from a
``search_materials`` tool call's ``SearchHit`` results — so the client can
render "*Calculus* §3.2, p.147" and link to it, not quote extracted text.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ChatRole = Literal["user", "assistant"]


class ChatCitation(BaseModel):
    material_id: str
    node_id: str
    title: str
    page: int


class ChatMessageOut(BaseModel):
    id: str
    seq: int
    role: ChatRole
    content: str
    citations: list[ChatCitation] = Field(default_factory=list)
    created_at: datetime


class ChatRequest(BaseModel):
    message: str
