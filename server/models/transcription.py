from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TranscriptionMetadata(BaseModel):
    job_id: str
    title: str
    original_filename: str
    transcription_date: str = ""
    source_type: str = "upload"     # "upload" | "youtube"
    video_url: Optional[str] = None
    video_id: Optional[str] = None
    file_type: Optional[str] = None


class TranscriptionResult(BaseModel):
    transcript: str
    metadata: TranscriptionMetadata
    job_id: str
    collection_id: str
