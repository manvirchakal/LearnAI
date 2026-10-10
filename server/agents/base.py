"""
Shared LangGraph agent state types and node utilities.
"""
from typing import Dict, List, Optional, TypedDict

from langchain_core.messages import BaseMessage


class ContentState(TypedDict):
    """State for the content (study materials) agent.

    Results are cached per (scope, unit_id): scope is a book's file_id with
    unit_id a section id, or "collections" with unit_id a collection id.
    """
    source_text: str
    user_id: str
    scope: str
    unit_id: str
    rag_file_id: Optional[str]      # restrict retrieval to one file, if set
    learning_profile: str
    force_regenerate: bool
    cached: bool
    rag_context: str
    narrative: str
    game_idea: str
    game_code: str
    diagrams: List[str]
    game_messages: List[BaseMessage]  # the game code conversation; retries continue it
    code_error: Optional[str]       # why the last game_code failed its check, fed back on retry
    retries: int
    error: Optional[str]


class DocumentState(TypedDict):
    """State for the document ingestion agent."""
    file_bytes: bytes
    filename: str
    user_id: str
    document_type: str
    toc_pages: Optional[str]        # "start-end" pages holding a printed TOC
    file_id: str
    local_key: str
    num_pages: int
    raw_toc: List[Dict]
    toc_source: str                 # "outline" | "vision" | "none"
    chapters: List[Dict]
    error: Optional[str]


class ChatState(TypedDict):
    """State for the chat agent."""
    user_message: str               # as typed by the user (persisted to history)
    query_message: str              # English version used for retrieval + prompting
    user_id: str
    scope: str
    unit_id: str
    rag_file_id: Optional[str]
    sources: List[Dict[str, str]]  # what the chat is about: {"source": id, "title"}; lengths added on load
    language: str
    narrative_summary: str
    learning_profile: str
    history: List[Dict]             # [{role, content}]
    ai_response: str
    error: Optional[str]


class MediaState(TypedDict):
    """State for the media ingestion agent."""
    source_type: str                # "youtube" | "upload"
    source_url: Optional[str]
    source_bytes: Optional[bytes]
    filename: Optional[str]         # original upload filename
    title: str
    user_id: str
    work_dir: str                   # temp dir owned by the caller
    audio_path: str
    video_id: str
    transcript: str
    job_id: str
    metadata: Dict
    collection_id: str
