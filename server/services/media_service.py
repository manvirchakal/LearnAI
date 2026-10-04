"""
Media primitives — YouTube audio download, local Whisper transcription, and
PowerPoint parsing. Orchestration (temp files, storage, embedding,
collections) for audio lives in agents/media_agent.py.
"""
import io
import logging
import uuid
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Tuple

from faster_whisper import WhisperModel
from pptx import Presentation

from core.config import settings
from services.rag_service import ingest_presentation
from services.storage_service import save_presentation_metadata, save_presentation_slide

logger = logging.getLogger(__name__)

# faster-whisper decodes through PyAV, so any container ffmpeg understands works.
SUPPORTED_MEDIA_FORMATS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".webm", ".mp4", ".mov", ".mkv"}


@lru_cache(maxsize=1)
def _whisper_model() -> WhisperModel:
    logger.info(f"Loading Whisper model: {settings.WHISPER_MODEL}")
    return WhisperModel(settings.WHISPER_MODEL, device="cpu", compute_type="int8")


def transcribe_file(audio_path: str | Path) -> str:
    """Transcribe a local audio/video file with faster-whisper."""
    segments, _ = _whisper_model().transcribe(str(audio_path), beam_size=5, vad_filter=True)
    return " ".join(seg.text.strip() for seg in segments)


def download_youtube_audio(url: str, dest_dir: str | Path) -> Tuple[Path, str, str]:
    """Download the best audio stream. Returns (path, title, video_id)."""
    from yt_dlp import YoutubeDL

    opts = {"format": "bestaudio/best", "outtmpl": str(Path(dest_dir) / "%(id)s.%(ext)s"),
            "quiet": True, "no_warnings": True, "noplaylist": True}
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        path = Path(ydl.prepare_filename(info))
    return path, info.get("title", "Untitled Video"), info.get("id", "")


def process_presentation(pptx_bytes: bytes, filename: str, user_id: str) -> dict:
    """Parse a .pptx, store its slides, embed its text, and file it in a collection."""
    from services.collection_service import create_default_collection

    presentation_id = uuid.uuid4().hex
    prs = Presentation(io.BytesIO(pptx_bytes))

    slides = []
    for num, slide in enumerate(prs.slides, 1):
        title = slide.shapes.title.text if slide.shapes.title is not None else ""
        content = [s.text.strip() for s in slide.shapes if getattr(s, "has_text_frame", False) and s.text.strip()]
        notes = ""
        if slide.has_notes_slide and slide.notes_slide.notes_text_frame is not None:
            notes = slide.notes_slide.notes_text_frame.text
        slides.append({"number": num, "title": title, "content": content, "notes": notes})

    metadata = {
        "presentation_id": presentation_id,
        "original_filename": filename,
        "upload_date": datetime.now().isoformat(),
        "total_slides": len(slides),
        "has_speaker_notes": any(s["notes"] for s in slides),
        "slide_titles": [s["title"] for s in slides if s["title"]],
    }
    save_presentation_metadata(user_id, presentation_id, metadata)
    for s in slides:
        save_presentation_slide(user_id, presentation_id, s["number"],
                                {"title": s["title"], "content": s["content"], "notes": s["notes"]})

    full_text = "\n\n".join(
        f"Slide {s['number']}: {s['title']}\n" + "\n".join(s["content"]) + (f"\nNotes: {s['notes']}" if s["notes"] else "")
        for s in slides
    )
    try:
        ingest_presentation(user_id, presentation_id, full_text)
    except Exception as e:
        logger.warning(f"Embedding presentation {presentation_id} failed: {e}")

    collection_id = create_default_collection("presentations", presentation_id, metadata, user_id)
    return {"presentation_id": presentation_id, "metadata": metadata, "collection_id": collection_id,
            "slides": [{"title": s["title"], "content": s["content"], "notes": s["notes"]} for s in slides]}
