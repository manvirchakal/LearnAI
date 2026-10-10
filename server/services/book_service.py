"""
Book service — CRUD and content access for uploaded PDFs.

Books are keyed by file_id; studyable units are sections keyed by the stable
ids assigned in utils/toc_utils.py. Ingestion orchestration (upload → TOC →
metadata) lives in agents/document_agent.py; this module only reads and
derives data from what the agent stored.
"""
import base64
import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Tuple

from core import storage
from services.rag_service import delete_file_chunks, ingest_section, source_id
from services.storage_service import (
    list_book_metadata,
    load_book_metadata,
    load_extracted_text,
    save_extracted_text,
)
from utils.pdf_utils import extract_section_pdf, extract_text_and_tables_pymupdf
from utils.toc_utils import find_section, iter_sections

logger = logging.getLogger(__name__)


class SectionNotFound(FileNotFoundError):
    pass


# ── TOC parsing via a vision model (used by the document agent) ────────────────

_TOC_PROMPT = """Analyze this table of contents and output ONLY a JSON object with this exact structure:
{
    "chapters": [
        {
            "number": "Chapter 1",
            "title": "Chapter Title",
            "page": 1,
            "sections": [{"title": "1.1 Section Title", "page": 3}]
        }
    ]
}
Rules:
1. "number" should be "Chapter X" (or "Prologue")
2. "page" must be an integer
3. Convert Roman numerals in titles to regular numbers
4. Output ONLY the JSON — no explanatory text"""


def parse_toc_with_llm(images: List[bytes]) -> List[Dict]:
    """Have the vision model read rendered TOC pages into raw chapters."""
    from langchain_core.messages import HumanMessage
    from core.llm import get_llm, image_block, message_text

    content: list = [{"type": "text", "text": _TOC_PROMPT}]
    for i, img in enumerate(images, 1):
        content.append(image_block(base64.b64encode(img).decode()))
        content.append({"type": "text", "text": f"This is page {i} of the table of contents."})

    raw = message_text(get_llm("vision", max_tokens=4096, temperature=0).invoke([HumanMessage(content=content)]))
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError("TOC parser returned no JSON")
    return json.loads(match.group(0)).get("chapters", [])


# ── Reads ─────────────────────────────────────────────────────────────────────

def book_pdf_path(user_id: str, file_id: str) -> Path:
    return storage.get_local_path(load_book_metadata(user_id, file_id)["local_key"])


def summarize(meta: Dict) -> Dict:
    chapters = meta.get("chapters", [])
    return {
        "file_id": meta["file_id"],
        "title": meta["title"],
        "filename": meta.get("filename", meta["title"]),
        "document_type": meta.get("document_type", "textbook"),
        "num_pages": meta.get("num_pages", 0),
        "chapter_count": len(chapters),
        "section_count": sum(len(c["sections"]) for c in chapters),
        "uploaded_at": meta.get("uploaded_at", ""),
    }


def list_books(user_id: str) -> List[Dict]:
    books = [summarize(m) for m in list_book_metadata(user_id) if "file_id" in m]
    return sorted(books, key=lambda b: b["uploaded_at"], reverse=True)


def get_book(user_id: str, file_id: str) -> Dict:
    meta = load_book_metadata(user_id, file_id)
    return {**summarize(meta), "chapters": meta.get("chapters", [])}


def get_section(user_id: str, file_id: str, section_id: str) -> Tuple[Dict, Dict]:
    meta = load_book_metadata(user_id, file_id)
    section = find_section(meta.get("chapters", []), section_id)
    if not section:
        raise SectionNotFound(f"Section {section_id} not found in {file_id}")
    return meta, section


def get_section_text(user_id: str, file_id: str, section_id: str) -> str:
    """Extract (and cache + embed) the text of one section."""
    cached = load_extracted_text(user_id, file_id, section_id)
    if cached:
        return cached

    meta, section = get_section(user_id, file_id, section_id)
    pdf_path = storage.get_local_path(meta["local_key"])
    text = extract_text_and_tables_pymupdf(pdf_path, section["start_page"], section["end_page"])
    save_extracted_text(user_id, file_id, section_id, text)
    ingest_section(user_id, file_id, section_id, text)
    return text


def section_source(user_id: str, file_id: str, section_id: str) -> Dict[str, str]:
    """The tutor's handle on a section: its source id and a title."""
    meta, section = get_section(user_id, file_id, section_id)
    return {"source": source_id(file_id, section_id), "title": f"{meta.get('title', '')}: {section['title']}"}


def get_section_pdf(user_id: str, file_id: str, section_id: str) -> Tuple[bytes, str]:
    meta, section = get_section(user_id, file_id, section_id)
    pdf_path = storage.get_local_path(meta["local_key"])
    data = extract_section_pdf(pdf_path, section["start_page"], section["end_page"])
    safe = "".join(c for c in section["title"] if c.isalnum() or c in " -_").strip() or section_id
    return data, f"{safe}.pdf"


# ── Writes ────────────────────────────────────────────────────────────────────

def index_book(user_id: str, file_id: str) -> None:
    """Extract and embed every section. Run as a background task after upload."""
    meta = load_book_metadata(user_id, file_id)
    for section in iter_sections(meta.get("chapters", [])):
        try:
            get_section_text(user_id, file_id, section["id"])
        except Exception as e:  # keep indexing the rest
            logger.warning(f"Indexing {file_id}/{section['id']} failed: {e}")
    logger.info(f"Indexed book {file_id} for {user_id}")


def delete_book(user_id: str, file_id: str) -> None:
    meta = load_book_metadata(user_id, file_id)
    storage.delete(meta["local_key"])
    storage.delete(f"metadata/{user_id}/{file_id}.json")
    for prefix in ("extracted-text", "narratives", "chat-history", "game-sessions"):
        storage.delete_prefix(f"{prefix}/{user_id}/{file_id}/")
    delete_file_chunks(user_id, file_id)
