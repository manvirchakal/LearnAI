import io
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
import tempfile
import os

from models.ai_outputs import SynthesizeSpeechRequest, TranslateRequest
from services.accessibility_service import translate_text, synthesize_speech

logger = logging.getLogger(__name__)
router = APIRouter(tags=["accessibility"])


@router.post("/translate")
async def translate_endpoint(request: TranslateRequest):
    if not request.text or not request.target_language:
        raise HTTPException(status_code=400, detail="text and target_language are required")
    result = translate_text(request.text, request.target_language)
    if result is None:
        raise HTTPException(status_code=500, detail="Translation failed or language pair not supported")
    return {"translated_text": result}


@router.post("/api/synthesize-speech")
async def synthesize_speech_endpoint(request: SynthesizeSpeechRequest):
    if not request.text:
        raise HTTPException(status_code=400, detail="text is required")
    try:
        audio_bytes = synthesize_speech(request.text, request.language)
        if not audio_bytes:
            raise HTTPException(status_code=500, detail="Speech synthesis failed")

        # Write to temp file and serve
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        return FileResponse(tmp_path, media_type="audio/wav", filename="speech.wav")
    except Exception as e:
        logger.error(f"TTS error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
