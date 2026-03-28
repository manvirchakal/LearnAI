"""
LangGraph document ingestion agent.
Pipeline: save_upload → extract_toc → parse_toc_llm → create_collections → embed_sections
"""
import logging
import uuid
from typing import Optional

from langgraph.graph import StateGraph, END

from agents.base import DocumentState
from services.storage_service import save_upload, save_metadata
from services.collection_service import create_textbook_collections
from services.textbook_service import _parse_toc_with_llm
from services.rag_service import ingest_section
from utils.pdf_utils import extract_toc, pages_to_images, extract_text_and_tables_pymupdf
from core import storage

logger = logging.getLogger(__name__)


def node_save_upload(state: DocumentState) -> DocumentState:
    try:
        unique_filename = f"{uuid.uuid4()}_{state['filename']}"
        local_key = save_upload(state["user_id"], unique_filename, state["file_bytes"])
        file_id = unique_filename.split("_")[0]
        return {**state, "local_key": local_key, "file_id": file_id}
    except Exception as e:
        return {**state, "error": str(e)}


def node_extract_toc(state: DocumentState) -> DocumentState:
    if state.get("error") or state["document_type"] != "textbook" or not state.get("toc_pages"):
        return state
    try:
        pdf_path = storage._resolve(state["local_key"])
        embedded = extract_toc(str(pdf_path))
        if embedded:
            chapters = {}
            for entry in embedded:
                if entry["level"] == 1:
                    chapters[entry["title"]] = {
                        "number": f"Chapter {len(chapters)+1}",
                        "title": entry["title"],
                        "page": entry["page"],
                        "sections": [],
                    }
                elif entry["level"] == 2:
                    last = list(chapters.values())[-1] if chapters else None
                    if last:
                        last["sections"].append({"title": entry["title"], "page": entry["page"]})
            return {**state, "toc_structure": list(chapters.values())}
        # No embedded TOC; will fall through to LLM parsing
        return state
    except Exception as e:
        logger.warning(f"TOC extraction failed: {e}, will try LLM parsing")
        return state


def node_parse_toc_llm(state: DocumentState) -> DocumentState:
    """Use Claude vision if embedded TOC wasn't found."""
    if state.get("error") or state.get("toc_structure") or not state.get("toc_pages"):
        return state
    try:
        pdf_path = storage._resolve(state["local_key"])
        start, end = map(int, state["toc_pages"].split("-"))
        images = pages_to_images(str(pdf_path), start, end)
        toc = _parse_toc_with_llm(images)
        return {**state, "toc_structure": toc}
    except Exception as e:
        logger.error(f"LLM TOC parsing failed: {e}")
        return {**state, "toc_structure": [], "error": str(e)}


def node_save_metadata(state: DocumentState) -> DocumentState:
    try:
        unique_filename = state["local_key"].split("/")[-1]
        metadata = {
            "title": state["filename"],
            "local_key": state["local_key"],
            "s3_key": state["local_key"],
            "user_id": state["user_id"],
            "document_type": state["document_type"],
            "table_of_contents": state.get("toc_structure", []),
        }
        save_metadata(state["user_id"], unique_filename, metadata)
        return state
    except Exception as e:
        return {**state, "error": str(e)}


def node_create_collections(state: DocumentState) -> DocumentState:
    if not state.get("toc_structure"):
        return state
    try:
        unique_filename = state["local_key"].split("/")[-1]
        file_id = state["file_id"]
        cols = create_textbook_collections(
            file_id, state["filename"], state["toc_structure"], state["local_key"], state["user_id"]
        )
        return {**state, "collections": cols}
    except Exception as e:
        logger.error(f"Collection creation failed: {e}")
        return {**state, "collections": {}}


def node_embed_sections(state: DocumentState) -> DocumentState:
    """Embed extracted text of all sections into ChromaDB."""
    if not state.get("toc_structure"):
        return state
    try:
        pdf_path = storage._resolve(state["local_key"])
        toc = state["toc_structure"]
        for chapter in toc:
            secs = chapter.get("sections", [])
            for i, sec in enumerate(secs):
                end = secs[i + 1]["page"] - 1 if i + 1 < len(secs) else sec["page"] + 50
                text = extract_text_and_tables_pymupdf(str(pdf_path), sec["page"], end)
                if text.strip():
                    ingest_section(state["user_id"], state["file_id"], sec["title"], text)
    except Exception as e:
        logger.warning(f"Section embedding failed: {e}")
    return state


def build_document_graph():
    g = StateGraph(DocumentState)
    g.add_node("save_upload", node_save_upload)
    g.add_node("extract_toc", node_extract_toc)
    g.add_node("parse_toc_llm", node_parse_toc_llm)
    g.add_node("save_metadata", node_save_metadata)
    g.add_node("create_collections", node_create_collections)
    g.add_node("embed_sections", node_embed_sections)

    g.set_entry_point("save_upload")
    g.add_edge("save_upload", "extract_toc")
    g.add_edge("extract_toc", "parse_toc_llm")
    g.add_edge("parse_toc_llm", "save_metadata")
    g.add_edge("save_metadata", "create_collections")
    g.add_edge("create_collections", "embed_sections")
    g.add_edge("embed_sections", END)
    return g.compile()


document_graph = build_document_graph()


def run_document_agent(
    file_bytes: bytes,
    filename: str,
    user_id: str,
    document_type: str = "textbook",
    toc_pages: Optional[str] = None,
) -> dict:
    initial: DocumentState = {
        "file_bytes": file_bytes,
        "filename": filename,
        "user_id": user_id,
        "file_id": "",
        "document_type": document_type,
        "toc_pages": toc_pages,
        "toc_structure": [],
        "local_key": "",
        "collections": {},
        "error": None,
    }
    result = document_graph.invoke(initial)
    return {
        "local_key": result["local_key"],
        "s3_key": result["local_key"],
        "collections": result.get("collections", {}),
        "error": result.get("error"),
    }
