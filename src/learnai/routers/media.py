"""Media API — lecture upload, YouTube import (both ``202`` + poll, like
``routers/materials.py``'s PDF upload — see its docstring), text
translation, and text-to-speech.

Translate and TTS are synchronous rather than job/poll: translation is
one cached LLM call and TTS is local, free, CPU synthesis of at most a
few seconds — neither is the kind of long-running work the 202 pattern
exists for (see the modernization plan's "Long-running jobs" section).
"""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, File, Response, UploadFile
from pydantic import BaseModel, Field

from learnai.deps import (
    ArqPoolDep,
    CurrentUser,
    JobRepoDep,
    LLMClientDep,
    MaterialRepoDep,
    StorageDep,
    TranslationRepoDep,
    TTSEngineDep,
)
from learnai.errors import ValidationError
from learnai.services.ingestion.media import ALLOWED_LECTURE_CONTENT_TYPES
from learnai.services.translation import translate_text

router = APIRouter(prefix="/api/v1/media", tags=["media"])

_MAX_LECTURE_UPLOAD_BYTES = 500 * 1024 * 1024  # 500 MiB — generous for an hour+ of audio/video


class UploadAccepted(BaseModel):
    material_id: str
    job_id: str
    poll_url: str


class YouTubeImportRequest(BaseModel):
    url: str = Field(min_length=1)


class TranslateRequest(BaseModel):
    text: str = Field(min_length=1)
    target_language: str = Field(min_length=1)


class TranslateResponse(BaseModel):
    translated_text: str


class TTSRequest(BaseModel):
    text: str = Field(min_length=1)
    language: str = Field(min_length=1)


@router.post("/lectures", response_model=UploadAccepted, status_code=202)
async def upload_lecture(
    user: CurrentUser,
    materials: MaterialRepoDep,
    jobs: JobRepoDep,
    storage: StorageDep,
    arq_pool: ArqPoolDep,
    file: UploadFile = File(...),
) -> UploadAccepted:
    if file.content_type not in ALLOWED_LECTURE_CONTENT_TYPES:
        raise ValidationError(f"unsupported content type: {file.content_type!r}")
    data = await file.read()
    if not data:
        raise ValidationError("uploaded file is empty")
    if len(data) > _MAX_LECTURE_UPLOAD_BYTES:
        raise ValidationError(f"file exceeds the {_MAX_LECTURE_UPLOAD_BYTES} byte upload limit")

    extension = Path(file.filename or "lecture").suffix or ".bin"
    storage_key = f"media/{user['_id']}/{uuid.uuid4().hex}{extension}"
    await storage.put(storage_key, data, file.content_type)

    material_id = await materials.create(
        filename=file.filename or "lecture",
        content_type=file.content_type,
        storage_key=storage_key,
        size_bytes=len(data),
        kind="lecture",
    )
    job_id = await jobs.create(
        kind="lecture_transcription", payload={"material_id": str(material_id)}
    )
    await arq_pool.enqueue_job(
        "transcribe_lecture_task",
        owner_id=str(user["_id"]),
        material_id=str(material_id),
        job_id=str(job_id),
    )

    return UploadAccepted(
        material_id=str(material_id), job_id=str(job_id), poll_url=f"/api/v1/jobs/{job_id}"
    )


@router.post("/youtube", response_model=UploadAccepted, status_code=202)
async def import_youtube(
    body: YouTubeImportRequest,
    user: CurrentUser,
    materials: MaterialRepoDep,
    jobs: JobRepoDep,
    arq_pool: ArqPoolDep,
) -> UploadAccepted:
    if not body.url.startswith(("http://", "https://")):
        raise ValidationError(f"not a URL: {body.url!r}")

    # Placeholder metadata — the real filename/size are only known after
    # the worker downloads the video (worker.tasks.import_youtube_task,
    # which calls MaterialRepository.update_source once it does). The
    # storage_key here is never fetched from StorageBackend; it's a
    # descriptive marker until the download replaces it with a real one.
    material_id = await materials.create(
        filename=body.url,
        content_type="audio/mp4",
        storage_key=f"youtube:{body.url}",
        size_bytes=0,
        kind="lecture",
    )
    job_id = await jobs.create(
        kind="youtube_import", payload={"material_id": str(material_id), "url": body.url}
    )
    await arq_pool.enqueue_job(
        "import_youtube_task",
        owner_id=str(user["_id"]),
        material_id=str(material_id),
        job_id=str(job_id),
        url=body.url,
    )

    return UploadAccepted(
        material_id=str(material_id), job_id=str(job_id), poll_url=f"/api/v1/jobs/{job_id}"
    )


@router.post("/translate", response_model=TranslateResponse)
async def translate(
    body: TranslateRequest, translations: TranslationRepoDep, llm: LLMClientDep
) -> TranslateResponse:
    translated = await translate_text(
        llm=llm, translations=translations, text=body.text, target_language=body.target_language
    )
    return TranslateResponse(translated_text=translated)


@router.post("/tts")
async def synthesize_speech(body: TTSRequest, user: CurrentUser, tts: TTSEngineDep) -> Response:
    audio = await tts.synthesize(body.text, language=body.language)
    return Response(content=audio, media_type="audio/wav")
