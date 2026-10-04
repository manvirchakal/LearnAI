"""
Media primitives — YouTube audio download, speech-to-text, and PowerPoint
parsing. Orchestration (temp files, storage, embedding, collections) for
audio lives in agents/media_agent.py.

STT_PROVIDER:
    openai  POST /audio/transcriptions on an OpenAI-compatible server (vLLM
            serving Whisper). Audio is re-encoded with ffmpeg into mono 16 kHz
            chunks so long lectures stay under the server's upload limit.
    local   faster-whisper in-process (needs the [local-ml] extra)
"""
import io
import logging
import shutil
import subprocess
import tempfile
import uuid
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import List, Tuple

from pptx import Presentation

from core.config import settings
from services.rag_service import ingest_presentation
from services.storage_service import save_presentation_metadata, save_presentation_slide

logger = logging.getLogger(__name__)

SUPPORTED_MEDIA_FORMATS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".webm", ".mp4", ".mov", ".mkv"}


@lru_cache(maxsize=1)
def _whisper_model():
    from faster_whisper import WhisperModel

    logger.info(f"Loading Whisper model: {settings.STT_MODEL}")
    return WhisperModel(settings.STT_MODEL, device="cpu", compute_type="int8")


@lru_cache(maxsize=1)
def _openai_client():
    from openai import OpenAI

    return OpenAI(base_url=settings.stt_base_url, api_key=settings.OPENAI_API_KEY, timeout=600)


def _split_audio(audio_path: Path, out_dir: Path) -> List[Path]:
    """Re-encode to mono 16 kHz MP3 chunks of STT_CHUNK_SECONDS (~2.5 MB per 10 min)."""
    if not shutil.which("ffmpeg"):
        logger.warning("ffmpeg not found; uploading audio unchunked")
        return [audio_path]
    pattern = out_dir / "chunk_%04d.mp3"
    subprocess.run(
        ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", str(audio_path), "-vn", "-ac", "1",
         "-ar", "16000", "-b:a", "32k", "-f", "segment", "-segment_time", str(settings.STT_CHUNK_SECONDS),
         str(pattern)],
        check=True, timeout=1800,
    )
    return sorted(out_dir.glob("chunk_*.mp3"))


def _transcribe_remote(audio_path: Path) -> str:
    with tempfile.TemporaryDirectory(prefix="learnai-stt-") as tmp:
        parts = []
        for chunk in _split_audio(audio_path, Path(tmp)):
            with open(chunk, "rb") as f:
                result = _openai_client().audio.transcriptions.create(
                    model=settings.STT_MODEL, file=(chunk.name, f), response_format="json")
            parts.append(result.text.strip())
    return " ".join(p for p in parts if p)


def transcribe_file(audio_path: str | Path) -> str:
    """Transcribe a local audio/video file with the configured STT provider."""
    if settings.STT_PROVIDER == "local":
        segments, _ = _whisper_model().transcribe(str(audio_path), beam_size=5, vad_filter=True)
        return " ".join(seg.text.strip() for seg in segments)
    return _transcribe_remote(Path(audio_path))


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
    metadata["collection_id"] = collection_id
    save_presentation_metadata(user_id, presentation_id, metadata)
    return {"presentation_id": presentation_id, "metadata": metadata, "collection_id": collection_id,
            "slides": [{"title": s["title"], "content": s["content"], "notes": s["notes"]} for s in slides]}
