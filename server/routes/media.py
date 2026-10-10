"""
Media API — transcripts (YouTube, recorded/uploaded lectures) and presentations.

    POST /media/youtube           {video_url}           (media agent, in the background) -> task
    GET  /media/tasks/{task_id}   a background task's progress, and its result when done
    POST /media/lectures          multipart audio+title (media agent)
    GET  /media/transcriptions
    GET  /media/transcriptions/{job_id}      metadata + transcript
    POST /media/presentations     multipart .pptx
    GET  /media/presentations
    GET  /media/presentations/{presentation_id}
"""
import logging

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile

from agents.media_agent import run_lecture_agent, run_youtube_agent
from core.dependencies import get_user_id
from services import task_service
from services.media_service import process_presentation
from services.storage_service import (
    list_presentation_metadata,
    list_transcription_metadata,
    load_presentation_metadata,
    load_presentation_slide,
    load_transcription,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/media", tags=["media"])


@router.post("/youtube", status_code=202)
def transcribe_youtube(video_url: str = Body(..., embed=True), user_id: str = Depends(get_user_id)):
    """Downloading and transcribing takes minutes: poll the returned task for progress."""
    return task_service.start_task(
        user_id, "youtube", lambda report: run_youtube_agent(video_url, user_id, on_progress=report))


@router.get("/tasks/{task_id}")
def get_task(task_id: str, user_id: str = Depends(get_user_id)):
    task = task_service.get_task(task_id, user_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found; it may have expired or the server restarted")
    return task


@router.post("/lectures")
def transcribe_lecture(
    audio: UploadFile = File(...),
    title: str = Form(...),
    user_id: str = Depends(get_user_id),
):
    try:
        return run_lecture_agent(audio.file.read(), audio.filename or "", title, user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Lecture transcription failed")
        raise HTTPException(status_code=502, detail=f"Transcription failed: {e}")


@router.get("/transcriptions")
def list_transcriptions(user_id: str = Depends(get_user_id)):
    return sorted(list_transcription_metadata(user_id),
                  key=lambda m: m.get("transcription_date", ""), reverse=True)


@router.get("/transcriptions/{job_id}")
def get_transcription(job_id: str, user_id: str = Depends(get_user_id)):
    try:
        return load_transcription(user_id, job_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Transcription not found")


@router.post("/presentations")
def upload_presentation(presentation: UploadFile = File(...), user_id: str = Depends(get_user_id)):
    if not (presentation.filename or "").lower().endswith(".pptx"):
        raise HTTPException(status_code=400, detail="Only .pptx files are supported")
    try:
        return process_presentation(presentation.file.read(), presentation.filename, user_id)
    except Exception as e:
        logger.exception("Presentation processing failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/presentations")
def list_presentations(user_id: str = Depends(get_user_id)):
    return sorted(list_presentation_metadata(user_id), key=lambda m: m.get("upload_date", ""), reverse=True)


@router.get("/presentations/{presentation_id}")
def get_presentation(presentation_id: str, user_id: str = Depends(get_user_id)):
    try:
        metadata = load_presentation_metadata(user_id, presentation_id)
        slides = [load_presentation_slide(user_id, presentation_id, n)
                  for n in range(1, metadata["total_slides"] + 1)]
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Presentation not found")
    return {"metadata": metadata, "slides": slides}
