"""
Accessibility API — local translation (argostranslate) and TTS (pyttsx3).

    POST /accessibility/translate  {text, target_language} → {translated_text}
    POST /accessibility/speech     {text, language}        → audio/wav
"""
import logging

from fastapi import APIRouter, HTTPException, Response

from models.accessibility import SynthesizeSpeechRequest, TranslateRequest
from services.accessibility_service import synthesize_speech, translate_text

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/accessibility", tags=["accessibility"])


@router.post("/translate")
def translate(request: TranslateRequest):
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="text is required")
    result = translate_text(request.text, request.target_language)
    if result is None:
        raise HTTPException(status_code=422, detail="Translation failed or language pair not installed")
    return {"translated_text": result}


@router.post("/speech")
def speech(request: SynthesizeSpeechRequest):
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="text is required")
    audio = synthesize_speech(request.text, request.language)
    if not audio:
        raise HTTPException(status_code=500, detail="Speech synthesis failed (is espeak installed?)")
    return Response(audio, media_type="audio/wav")
