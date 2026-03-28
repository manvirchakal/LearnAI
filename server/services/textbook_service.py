"""
Textbook service — PDF upload, TOC extraction, section extraction.
Replaces S3 upload + AWS Textract + inline processing from main.py.
"""
import base64
import logging
import os
import tempfile
import uuid
from pathlib import Path
from typing import List, Dict, Optional

from core.llm import invoke_llm
from core import storage
from services.storage_service import save_upload, save_metadata, load_metadata, list_metadata
from services.rag_service import ingest_section
from services.collection_service import create_textbook_collections
from utils.pdf_utils import (
    extract_toc,
    pages_to_images,
    extract_section_pdf,
    extract_text_and_tables_pymupdf,
)

logger = logging.getLogger(__name__)


def _build_toc_prompt(images: List[bytes]) -> list:
    """Build Claude multimodal message content for TOC parsing."""
    content = [
        {
            "type": "text",
            "text": """Analyze this table of contents and output ONLY a JSON object with this exact structure:
{
    "chapters": [
        {
            "number": "Chapter 1",
            "title": "Chapter Title",
            "page": 1,
            "sections": []
        }
    ]
}
Rules:
1. "number" should be "Chapter X" (or "Prologue")
2. "page" must be an integer
3. Convert Roman numerals in titles to regular numbers
4. Output ONLY the JSON — no explanatory text""",
        }
    ]
    for i, img_bytes in enumerate(images, 1):
        content.extend([
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                          "data": base64.b64encode(img_bytes).decode()}},
            {"type": "text", "text": f"This is page {i} of the table of contents."},
        ])
    return content


def _parse_toc_with_llm(images: List[bytes]) -> List[Dict]:
    """Use Claude vision to parse TOC images into structured chapters."""
    import json
    from langchain_core.messages import HumanMessage
    from core.llm import get_sonnet

    llm = get_sonnet()
    content = _build_toc_prompt(images)
    response = llm.invoke([HumanMessage(content=content)])

    raw = response.content.strip()
    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    toc_data = json.loads(raw.strip())
    chapters = []
    for ch in toc_data.get("chapters", []):
        chapters.append({
            "number": ch.get("number", ""),
            "title": ch.get("title", ""),
            "page": ch.get("page", 1),
            "sections": ch.get("sections", []),
        })
    return chapters


def _get_pdf_local_path(user_id: str, unique_filename: str) -> Path:
    return storage._resolve(f"user-uploads/{user_id}/{unique_filename}")


async def upload_pdf(
    file_bytes: bytes,
    filename: str,
    document_type: str,
    user_id: str,
    toc_pages: Optional[str] = None,
) -> dict:
    """
    Upload a PDF: save locally, extract TOC, create collections.
    Replaces the old upload_pdf + process_toc_pages pipeline.
    """
    unique_filename = f"{uuid.uuid4()}_{filename}"
    local_key = save_upload(user_id, unique_filename, file_bytes)
    file_id = unique_filename.split("_")[0]

    metadata = {
        "title": filename,
        "local_key": local_key,
        "s3_key": local_key,          # backward compat alias
        "user_id": user_id,
        "document_type": document_type,
        "table_of_contents": [],
    }

    collections_info = None

    if document_type == "textbook" and toc_pages:
        logger.info(f"Processing TOC pages {toc_pages} for {filename}")
        start_page, end_page = map(int, toc_pages.split("-"))
        pdf_path = _get_pdf_local_path(user_id, unique_filename)

        # Try embedded TOC first; fall back to Claude vision
        toc_structure = extract_toc(str(pdf_path))
        if toc_structure:
            # Convert flat toc entries to chapter/section structure
            chapters: Dict = {}
            for entry in toc_structure:
                if entry["level"] == 1:
                    chapters[entry["title"]] = {"number": f"Chapter {len(chapters)+1}",
                                                 "title": entry["title"], "page": entry["page"], "sections": []}
                elif entry["level"] == 2:
                    last = list(chapters.values())[-1] if chapters else None
                    if last:
                        last["sections"].append({"title": entry["title"], "page": entry["page"]})
            toc_structure = list(chapters.values())
        else:
            # Fall back to Claude vision parsing
            images = pages_to_images(str(pdf_path), start_page, end_page)
            toc_structure = _parse_toc_with_llm(images)

        metadata["table_of_contents"] = toc_structure
        collections_info = create_textbook_collections(file_id, filename, toc_structure, local_key, user_id)

    save_metadata(user_id, unique_filename, metadata)

    response = {"message": "PDF uploaded successfully", "local_key": local_key, "s3_key": local_key}
    if collections_info:
        response["collections"] = collections_info
    return response


def get_user_books(user_id: str) -> List[dict]:
    books = []
    for meta in list_metadata(user_id):
        books.append({"title": meta.get("title", ""), "s3_key": meta.get("local_key", meta.get("s3_key", ""))})
    return books


def get_user_textbooks(user_id: str) -> List[dict]:
    textbooks = []
    for meta in list_metadata(user_id):
        if meta.get("document_type") == "textbook":
            textbooks.append({
                "title": meta.get("title", ""),
                "s3_key": meta.get("local_key", meta.get("s3_key", "")),
            })
    return textbooks


def get_textbook_structure(user_id: str, file_id: str, filename: str) -> dict:
    meta = load_metadata(user_id, f"{file_id}_{filename}")
    toc = meta.get("table_of_contents", [])
    chapters = []
    for chapter in toc:
        chapters.append({
            "id": chapter["number"],
            "title": f"{chapter['number']}: {chapter['title']}",
            "sections": [
                {"id": s["title"].split()[0], "title": s["title"]}
                for s in chapter.get("sections", [])
            ],
        })
    return {"chapters": chapters}


def get_section_pdf_bytes(
    user_id: str, file_id: str, filename: str, section_id: str
) -> tuple[bytes, str]:
    """Extract section pages as a PDF. Returns (bytes, sanitized_filename)."""
    meta = load_metadata(user_id, f"{file_id}_{filename}")
    toc = meta.get("table_of_contents", [])

    section = next_section = None
    for chapter in toc:
        secs = chapter.get("sections", [])
        for i, s in enumerate(secs):
            if s["title"].startswith(section_id):
                section = s
                if i + 1 < len(secs):
                    next_section = secs[i + 1]
                break
        if section:
            break

    if not section:
        raise FileNotFoundError(f"Section {section_id} not found")

    end_page = next_section["page"] - 1 if next_section else section["page"] + 50
    pdf_path = _get_pdf_local_path(user_id, f"{file_id}_{filename}")
    pdf_bytes = extract_section_pdf(str(pdf_path), section["page"], end_page)

    sanitized = "".join(c for c in section["title"] if c.isalnum() or c in " -_").rstrip()
    return pdf_bytes, f"{sanitized}.pdf"


def process_pdf_section(
    user_id: str, file_id: str, filename: str, section_name: str
) -> str:
    """Extract text from a section using PyMuPDF, cache result, and ingest into ChromaDB."""
    from services.storage_service import save_extracted_text, load_extracted_text

    # Check cache
    existing = load_extracted_text(user_id, file_id, section_name)
    if existing:
        return existing

    meta = load_metadata(user_id, f"{file_id}_{filename}")
    toc = meta.get("table_of_contents", [])

    section = next_section = None
    for chapter in toc:
        secs = chapter.get("sections", [])
        for i, s in enumerate(secs):
            if s["title"] == section_name:
                section = s
                if i + 1 < len(secs):
                    next_section = secs[i + 1]
                break
        if section:
            break

    if not section:
        raise FileNotFoundError(f"Section {section_name} not found in TOC")

    end_page = next_section["page"] - 1 if next_section else section["page"] + 50
    pdf_path = _get_pdf_local_path(user_id, f"{file_id}_{filename}")

    extracted = extract_text_and_tables_pymupdf(str(pdf_path), section["page"], end_page)
    save_extracted_text(user_id, file_id, section_name, extracted)
    ingest_section(user_id, file_id, section_name, extracted)

    return extracted
