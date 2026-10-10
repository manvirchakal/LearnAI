from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class NotesMetadata(BaseModel):
    notes_id: str
    original_filename: str
    upload_date: str
    file_type: str
    processing_status: str = "completed"
    has_diagrams: bool = False
    has_tables: bool = False


class ProcessedNotes(BaseModel):
    text_content: List[Dict[str, Any]] = []
    diagrams: List[Dict[str, Any]] = []
    tables: List[Dict[str, Any]] = []
