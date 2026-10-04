"""
Storage service — thin wrapper over core/storage.py.
Provides semantic helpers that mirror the old S3 patterns used in routes/services.
"""
from core import storage
from typing import Any, List


# ── Learning profiles ─────────────────────────────────────────────────────────

def save_profile(user_id: str, profile: dict) -> None:
    storage.save_json(f"learning_profiles/{user_id}.json", profile)


def load_profile(user_id: str) -> dict:
    return storage.load_json(f"learning_profiles/{user_id}.json")


def profile_exists(user_id: str) -> bool:
    return storage.json_exists(f"learning_profiles/{user_id}.json")


# ── Books (uploaded PDFs) ──────────────────────────────────────────────────────

def save_upload(user_id: str, file_id: str, data: bytes) -> str:
    key = f"user-uploads/{user_id}/{file_id}.pdf"
    storage.save_bytes(key, data)
    return key


def save_book_metadata(user_id: str, file_id: str, metadata: dict) -> None:
    storage.save_json(f"metadata/{user_id}/{file_id}.json", metadata)


def load_book_metadata(user_id: str, file_id: str) -> dict:
    return storage.load_json(f"metadata/{user_id}/{file_id}.json")


def list_book_metadata(user_id: str) -> List[dict]:
    results = []
    for key in storage.list_json_keys(f"metadata/{user_id}/"):
        try:
            results.append(storage.load_json(key))
        except Exception:
            pass
    return results


# ── Per-section artifacts (keyed by stable section ids, never titles) ─────────

def save_extracted_text(user_id: str, file_id: str, section_id: str, text: str) -> None:
    storage.save_text(f"extracted-text/{user_id}/{file_id}/{section_id}.txt", text)


def load_extracted_text(user_id: str, file_id: str, section_id: str) -> str:
    key = f"extracted-text/{user_id}/{file_id}/{section_id}.txt"
    return storage.load_text(key) if storage.json_exists(key) else ""


def save_study_materials(user_id: str, scope: str, unit_id: str, data: dict) -> None:
    """scope is a file_id for book sections, or "collections" for collections."""
    storage.save_json(f"narratives/{user_id}/{scope}/{unit_id}.json", data)


def load_study_materials(user_id: str, scope: str, unit_id: str) -> dict:
    key = f"narratives/{user_id}/{scope}/{unit_id}.json"
    return storage.load_json(key) if storage.json_exists(key) else {}


def save_chat_history(user_id: str, scope: str, unit_id: str, history: list) -> None:
    storage.save_json(f"chat-history/{user_id}/{scope}/{unit_id}.json", history)


def load_chat_history(user_id: str, scope: str, unit_id: str) -> list:
    key = f"chat-history/{user_id}/{scope}/{unit_id}.json"
    return storage.load_json(key) if storage.json_exists(key) else []


# ── Collections ───────────────────────────────────────────────────────────────

def save_collection(user_id: str, collection_id: str, data: dict) -> None:
    storage.save_json(f"collections/{user_id}/{collection_id}.json", data)


def load_collection(user_id: str, collection_id: str) -> dict:
    return storage.load_json(f"collections/{user_id}/{collection_id}.json")


def list_collections(user_id: str) -> List[dict]:
    keys = storage.list_json_keys(f"collections/{user_id}/")
    results = []
    for key in keys:
        try:
            results.append(storage.load_json(key))
        except Exception:
            pass
    return results


# ── Transcriptions ────────────────────────────────────────────────────────────

def save_transcription_metadata(user_id: str, job_id: str, metadata: dict) -> None:
    storage.save_json(f"transcriptions/{user_id}/metadata/{job_id}.json", metadata)


def save_transcription_content(user_id: str, job_id: str, text: str) -> None:
    storage.save_text(f"transcriptions/{user_id}/content/{job_id}.txt", text)


def list_transcription_metadata(user_id: str) -> List[dict]:
    keys = storage.list_json_keys(f"transcriptions/{user_id}/metadata/")
    results = []
    for key in keys:
        try:
            results.append(storage.load_json(key))
        except Exception:
            pass
    return results


# ── Presentations ─────────────────────────────────────────────────────────────

def save_presentation_metadata(user_id: str, pres_id: str, metadata: dict) -> None:
    storage.save_json(f"presentations/{user_id}/metadata/{pres_id}.json", metadata)


def save_presentation_slide(user_id: str, pres_id: str, slide_num: int, content: dict) -> None:
    storage.save_json(f"presentations/{user_id}/content/{pres_id}/slide_{slide_num}.json", content)


def load_presentation_metadata(user_id: str, pres_id: str) -> dict:
    return storage.load_json(f"presentations/{user_id}/metadata/{pres_id}.json")


def load_presentation_slide(user_id: str, pres_id: str, slide_num: int) -> dict:
    return storage.load_json(f"presentations/{user_id}/content/{pres_id}/slide_{slide_num}.json")


def list_presentation_metadata(user_id: str) -> List[dict]:
    keys = storage.list_json_keys(f"presentations/{user_id}/metadata/")
    results = []
    for key in keys:
        try:
            results.append(storage.load_json(key))
        except Exception:
            pass
    return results


# ── Notes ─────────────────────────────────────────────────────────────────────

def save_notes_metadata(user_id: str, notes_id: str, metadata: dict) -> None:
    storage.save_json(f"notes/{user_id}/metadata/{notes_id}.json", metadata)


def save_notes_content(user_id: str, notes_id: str, content: dict) -> None:
    storage.save_json(f"notes/{user_id}/processed/{notes_id}.json", content)


def load_notes_metadata(user_id: str, notes_id: str) -> dict:
    return storage.load_json(f"notes/{user_id}/metadata/{notes_id}.json")


def load_notes_content(user_id: str, notes_id: str) -> dict:
    return storage.load_json(f"notes/{user_id}/processed/{notes_id}.json")
