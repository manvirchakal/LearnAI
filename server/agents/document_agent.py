"""
LangGraph document ingestion agent — turns an uploaded PDF into a studyable book.

    save_upload ▶ read_outline ─┬─(outline found)──────────────▶ normalize ▶ save_metadata ▶ END
                                ├─(toc_pages given)▶ parse_toc_vision ─┘
                                ├─(toc_pages, vision off)▶ vision_disabled ─▶ normalize
                                └─(neither)────────────────────▶ normalize

Section text extraction and embedding are not part of this graph: they run
lazily per section, or for the whole book as a background task after upload
(services/book_service.index_book), so the upload request returns quickly.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from langgraph.graph import END, StateGraph

from agents.base import DocumentState
from core import storage
from core.config import settings
from services.book_service import parse_toc_with_llm
from services.storage_service import save_book_metadata, save_upload
from utils.pdf_utils import extract_toc, page_count, pages_to_images
from utils.toc_utils import normalize_toc, single_section_toc, toc_from_outline

logger = logging.getLogger(__name__)


def node_save_upload(state: DocumentState) -> dict:
    file_id = uuid.uuid4().hex
    local_key = save_upload(state["user_id"], file_id, state["file_bytes"])
    return {"file_id": file_id, "local_key": local_key,
            "num_pages": page_count(storage.get_local_path(local_key))}


def node_read_outline(state: DocumentState) -> dict:
    try:
        raw = toc_from_outline(extract_toc(storage.get_local_path(state["local_key"])))
    except Exception as e:
        logger.warning(f"Reading PDF outline failed: {e}")
        raw = []
    return {"raw_toc": raw, "toc_source": "outline" if raw else "none"}


def node_parse_toc_vision(state: DocumentState) -> dict:
    try:
        start, end = (int(p) for p in state["toc_pages"].split("-"))
        images = pages_to_images(storage.get_local_path(state["local_key"]), start, end)
        raw = parse_toc_with_llm(images)
        return {"raw_toc": raw, "toc_source": "vision" if raw else "none"}
    except Exception as e:
        # A bad TOC parse shouldn't fail the upload; fall back to a single section
        logger.error(f"Vision TOC parsing failed: {e}")
        return {"raw_toc": [], "toc_source": "none", "error": f"TOC parsing failed: {e}"}


def node_normalize(state: DocumentState) -> dict:
    chapters = normalize_toc(state["raw_toc"], state["num_pages"])
    if not chapters:
        chapters = single_section_toc(state["filename"].removesuffix(".pdf"), state["num_pages"])
    return {"chapters": chapters}


def node_save_metadata(state: DocumentState) -> dict:
    save_book_metadata(state["user_id"], state["file_id"], {
        "file_id": state["file_id"],
        "title": state["filename"].removesuffix(".pdf"),
        "filename": state["filename"],
        "local_key": state["local_key"],
        "user_id": state["user_id"],
        "document_type": state["document_type"],
        "num_pages": state["num_pages"],
        "toc_source": state["toc_source"],
        "chapters": state["chapters"],
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    })
    return {}


def route_after_outline(state: DocumentState) -> str:
    if state["raw_toc"] or not state.get("toc_pages"):
        return "normalize"
    return "vision" if settings.LLM_VISION_ENABLED else "vision_disabled"


def node_vision_disabled(state: DocumentState) -> dict:
    return {"error": "TOC pages were given but LLM_VISION_ENABLED is off; the book was imported as one section"}


def build_document_graph():
    g = StateGraph(DocumentState)
    g.add_node("save_upload", node_save_upload)
    g.add_node("read_outline", node_read_outline)
    g.add_node("parse_toc_vision", node_parse_toc_vision)
    g.add_node("vision_disabled", node_vision_disabled)
    g.add_node("normalize", node_normalize)
    g.add_node("save_metadata", node_save_metadata)

    g.set_entry_point("save_upload")
    g.add_edge("save_upload", "read_outline")
    g.add_conditional_edges("read_outline", route_after_outline,
                            {"normalize": "normalize", "vision": "parse_toc_vision",
                             "vision_disabled": "vision_disabled"})
    g.add_edge("parse_toc_vision", "normalize")
    g.add_edge("vision_disabled", "normalize")
    g.add_edge("normalize", "save_metadata")
    g.add_edge("save_metadata", END)
    return g.compile()


document_graph = build_document_graph()


def run_document_agent(file_bytes: bytes, filename: str, user_id: str,
                       document_type: str = "textbook", toc_pages: Optional[str] = None) -> dict:
    """Ingest a PDF. Returns {"file_id", "toc_source", "warning"}."""
    result = document_graph.invoke({
        "file_bytes": file_bytes,
        "filename": filename,
        "user_id": user_id,
        "document_type": document_type,
        "toc_pages": toc_pages or None,
        "file_id": "",
        "local_key": "",
        "num_pages": 0,
        "raw_toc": [],
        "toc_source": "none",
        "chapters": [],
        "error": None,
    })
    return {"file_id": result["file_id"], "toc_source": result["toc_source"], "warning": result.get("error")}
