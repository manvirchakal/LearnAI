from pydantic import BaseModel
from typing import List, Optional


class SlideContent(BaseModel):
    number: int
    title: str = ""
    content: List[str] = []
    notes: str = ""


class PresentationMetadata(BaseModel):
    presentation_id: str
    original_filename: str
    upload_date: str
    total_slides: int
    has_speaker_notes: bool = False
    slide_titles: List[str] = []
