"""
Shared LangGraph agent state types and node utilities.
"""
from typing import Annotated, Any, Dict, List, Optional, TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class ContentState(TypedDict):
    """State for the content generation agent."""
    section_text: str
    user_id: str
    file_id: str
    section_name: str
    learning_profile: str
    force_regenerate: bool
    rag_context: str
    narrative: str
    game_idea: str
    game_code: str
    diagrams: List[str]
    code_valid: bool
    retries: int
    error: Optional[str]


class DocumentState(TypedDict):
    """State for the document ingestion agent."""
    file_bytes: bytes
    filename: str
    user_id: str
    file_id: str
    document_type: str
    toc_pages: Optional[str]
    toc_structure: List[Dict]
    local_key: str
    collections: Dict
    error: Optional[str]


class ChatState(TypedDict):
    """State for the chat agent."""
    messages: Annotated[List[BaseMessage], add_messages]
    user_message: str
    user_id: str
    file_id: str
    section_name: str
    language: str
    force_regenerate: str
    extracted_text: str
    narrative_summary: str
    rag_context: str
    learning_profile: str
    history: List[Dict]
    ai_response: str
    error: Optional[str]


class MediaState(TypedDict):
    """State for the media ingestion agent."""
    source_type: str        # "youtube" | "upload"
    source_url: Optional[str]
    source_bytes: Optional[bytes]
    filename: Optional[str]
    title: Optional[str]
    user_id: str
    transcript: str
    job_id: str
    collection_id: str
    error: Optional[str]
