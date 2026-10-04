"""
Collection service — CRUD for study collections.
"""
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from services.book_service import get_section_text
from services.storage_service import (
    save_collection,
    load_collection,
    list_collections,
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


def get_collection_content(collection_id: str, user_id: str) -> Dict:
    """Aggregate all material text from a collection for use in prompts."""
    col = get_collection(collection_id, user_id)
    content: Dict = {"textbook_content": [], "transcriptions": [], "presentations": [], "notes": []}

    # Textbook sections are referenced as {"file_id": ..., "section_id": ...}
    for ref in col.get("materials", {}).get("textbook_sections", []):
        file_id, section_id = ref.get("file_id"), ref.get("section_id")
        if not (file_id and section_id):
            continue
        try:
            content["textbook_content"].append({"text": get_section_text(user_id, file_id, section_id)})
        except FileNotFoundError:
            logger.warning(f"Collection {collection_id} references missing section {file_id}/{section_id}")

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
