"""
Collection service — CRUD for study collections.
"""
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from services.storage_service import (
    save_collection,
    load_collection,
    list_collections,
    load_extracted_text,
)
from core import storage

logger = logging.getLogger(__name__)


def create_collection(name: str, materials: Dict, user_id: str) -> dict:
    collection_id = str(uuid.uuid4())
    collection = {
        "collection_id": collection_id,
        "name": name,
        "created_date": datetime.now().isoformat(),
        "user_id": user_id,
        "materials": materials,
    }
    save_collection(user_id, collection_id, collection)
    return collection


def get_collection(collection_id: str, user_id: str) -> dict:
    col = load_collection(user_id, collection_id)
    if col.get("user_id") != user_id:
        raise PermissionError("Not authorized to access this collection")
    return col


def list_user_collections(user_id: str) -> List[dict]:
    """Return all collections with more than one material."""
    results = []
    for col in list_collections(user_id):
        total = sum(len(v) for v in col.get("materials", {}).values() if isinstance(v, list))
        if total > 1:
            results.append(col)
    return results


def update_collection_materials(collection_id: str, materials: Dict, user_id: str) -> dict:
    col = load_collection(user_id, collection_id)
    if col.get("user_id") != user_id:
        raise PermissionError("Not authorized to modify this collection")
    col["materials"] = materials
    save_collection(user_id, collection_id, col)
    return col


def create_default_collection(
    material_type: str, material_id: str, material_metadata: Dict, user_id: str
) -> str:
    """Create a single-item collection for a newly processed material."""
    collection_id = str(uuid.uuid4())
    id_key = f"{material_type[:-1]}_id" if material_type.endswith("s") else f"{material_type}_id"
    collection = {
        "collection_id": collection_id,
        "name": f"{material_metadata.get('original_filename', 'Untitled')} Collection",
        "created_date": datetime.now().isoformat(),
        "user_id": user_id,
        "materials": {
            "textbook_sections": [],
            "transcriptions": [],
            "presentations": [],
            "notes": [],
        },
    }
    collection["materials"][material_type].append(
        {id_key: material_id, "added_date": datetime.now().isoformat()}
    )
    save_collection(user_id, collection_id, collection)
    return collection_id


def create_textbook_collections(
    file_id: str, book_title: str, toc_structure: List[Dict], local_key: str, user_id: str
) -> Dict:
    """Create per-section and per-chapter collections for a textbook."""
    collections: Dict = {"book_id": file_id, "section_collections": [], "chapter_collections": []}

    for chapter in toc_structure:
        chapter_sections = chapter.get("sections", [])
        chapter_collection_id = str(uuid.uuid4())
        section_ids = []

        for section in chapter_sections:
            section_id = str(uuid.uuid4())
            section_col = {
                "collection_id": section_id,
                "name": f"{book_title} - {section['title']}",
                "created_date": datetime.now().isoformat(),
                "user_id": user_id,
                "parent_chapter": chapter["number"],
                "materials": {
                    "textbook_sections": [{
                        "section_id": section_id,
                        "title": section["title"],
                        "page": section["page"],
                        "local_key": local_key,
                        "added_date": datetime.now().isoformat(),
                    }],
                    "transcriptions": [],
                    "presentations": [],
                    "notes": [],
                },
            }
            save_collection(user_id, section_id, section_col)
            section_ids.append(section_id)
            collections["section_collections"].append(section_col)

        chapter_col = {
            "collection_id": chapter_collection_id,
            "name": f"{book_title} - {chapter['number']}: {chapter['title']}",
            "created_date": datetime.now().isoformat(),
            "user_id": user_id,
            "chapter_number": chapter["number"],
            "materials": {
                "textbook_sections": [
                    {"section_id": str(uuid.uuid4()), "title": s["title"], "page": s["page"],
                     "local_key": local_key, "added_date": datetime.now().isoformat()}
                    for s in chapter_sections
                ],
                "transcriptions": [],
                "presentations": [],
                "notes": [],
                "subcollections": section_ids,
            },
        }
        save_collection(user_id, chapter_collection_id, chapter_col)
        collections["chapter_collections"].append(chapter_col)

    return collections


def get_collection_content(collection_id: str, user_id: str) -> Dict:
    """Aggregate all material text from a collection for use in prompts."""
    col = get_collection(collection_id, user_id)
    content: Dict = {"textbook_content": [], "transcriptions": [], "presentations": [], "notes": []}

    for section in col.get("materials", {}).get("textbook_sections", []):
        file_id = section.get("file_id", "")
        section_title = section.get("title", "")
        if file_id and section_title:
            text = load_extracted_text(user_id, file_id, section_title)
            if text:
                content["textbook_content"].append({"text": text})

    for trans in col.get("materials", {}).get("transcriptions", []):
        trans_id = trans.get("transcription_id") or trans.get("job_id", "")
        key = f"transcriptions/{user_id}/content/{trans_id}.txt"
        try:
            content["transcriptions"].append(storage.load_text(key))
        except Exception:
            pass

    for pres in col.get("materials", {}).get("presentations", []):
        pres_id = pres.get("presentation_id", "")
        keys = storage.list_json_keys(f"presentations/{user_id}/content/{pres_id}/")
        slides = []
        for k in sorted(keys):
            try:
                slides.append(storage.load_json(k))
            except Exception:
                pass
        if slides:
            content["presentations"].append({"slides": slides})

    for note in col.get("materials", {}).get("notes", []):
        notes_id = note.get("notes_id", "")
        key = f"notes/{user_id}/processed/{notes_id}.json"
        try:
            content["notes"].append(storage.load_json(key))
        except Exception:
            pass

    return content
