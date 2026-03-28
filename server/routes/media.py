import logging
from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile

from core.dependencies import get_user_id
from services.media_service import transcribe_youtube, transcribe_lecture, process_presentation
from services.storage_service import list_transcription_metadata, list_presentation_metadata, load_presentation_metadata
from services.storage_service import load_presentation_slide

logger = logging.getLogger(__name__)
router = APIRouter(tags=["media"])


@router.post("/transcribe-youtube")
async def transcribe_youtube_endpoint(
    video_url: str = Body(..., embed=True),
    user_id: str = Depends(get_user_id),
):
    try:
        return await transcribe_youtube(video_url, user_id)
    except Exception as e:
        logger.error(f"YouTube transcription error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transcribe-lecture")
async def transcribe_lecture_endpoint(
    audio: UploadFile = File(...),
    title: str = Form(...),
    user_id: str = Depends(get_user_id),
):
    try:
        audio_bytes = await audio.read()
        return await transcribe_lecture(audio_bytes, audio.filename, title, user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Lecture transcription error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process-presentation")
async def process_presentation_endpoint(
    presentation: UploadFile = File(...),
    user_id: str = Depends(get_user_id),
):
    if not presentation.filename.endswith(".pptx"):
        raise HTTPException(status_code=400, detail="Only .pptx files are supported")
    try:
        pptx_bytes = await presentation.read()
        return process_presentation(pptx_bytes, presentation.filename, user_id)
    except Exception as e:
        logger.error(f"Presentation processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user-transcriptions")
async def user_transcriptions(user_id: str = Depends(get_user_id)):
    return list_transcription_metadata(user_id)


@router.get("/list-presentations/{user_id_path}")
async def list_presentations(user_id_path: str, user_id: str = Depends(get_user_id)):
    return list_presentation_metadata(user_id_path)


@router.get("/get-presentation/{user_id_path}/{presentation_id}")
async def get_presentation(
    user_id_path: str,
    presentation_id: str,
    format: str = "separate",
    user_id: str = Depends(get_user_id),
):
    try:
        metadata = load_presentation_metadata(user_id_path, presentation_id)
        slides = [
            load_presentation_slide(user_id_path, presentation_id, n)
            for n in range(1, metadata["total_slides"] + 1)
        ]
        if format == "consolidated":
            return {"metadata": metadata, "content": {f"slide_{i+1}": s for i, s in enumerate(slides)}}
        return {"metadata": metadata, "slides": slides}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Presentation not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
