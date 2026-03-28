"""
Local TTS (pyttsx3) and translation (argostranslate).
Replaces AWS Polly and AWS Translate.
"""
import io
import logging
import os
import tempfile
from typing import Optional

logger = logging.getLogger(__name__)


# ── Translation ───────────────────────────────────────────────────────────────

def translate_text(text: str, target_language: str) -> Optional[str]:
    """
    Translate text using argostranslate (offline).
    Source language is always English ('en').
    On first use per language pair, downloads the package automatically.
    """
    try:
        from argostranslate import package, translate
        installed_languages = translate.get_installed_languages()
        from_lang = next((l for l in installed_languages if l.code == "en"), None)
        to_lang = next((l for l in installed_languages if l.code == target_language), None)

        if not from_lang or not to_lang:
            logger.info(f"Installing argostranslate package for en→{target_language}")
            package.update_package_index()
            available = package.get_available_packages()
            pkg = next(
                (p for p in available if p.from_code == "en" and p.to_code == target_language),
                None,
            )
            if not pkg:
                logger.warning(f"No argostranslate package found for en→{target_language}")
                return None
            package.install_from_path(pkg.download())
            installed_languages = translate.get_installed_languages()
            from_lang = next((l for l in installed_languages if l.code == "en"), None)
            to_lang = next((l for l in installed_languages if l.code == target_language), None)

        if not from_lang or not to_lang:
            return None

        translation = from_lang.get_translation(to_lang)
        return translation.translate(text)
    except Exception as e:
        logger.error(f"Translation error (en→{target_language}): {e}")
        return None


# ── Text-to-Speech ────────────────────────────────────────────────────────────

def synthesize_speech(text: str, language: str = "en-US") -> bytes:
    """
    Synthesize speech locally using pyttsx3.
    Returns raw MP3/WAV bytes.
    Falls back to empty bytes on error.
    """
    try:
        import pyttsx3
        engine = pyttsx3.init()

        # pyttsx3 doesn't support language codes directly; adjust rate/voice if available
        voices = engine.getProperty("voices")
        # Try to match language prefix (e.g., "en" from "en-US")
        lang_prefix = language.split("-")[0].lower()
        for voice in voices:
            if lang_prefix in voice.languages or lang_prefix in voice.id.lower():
                engine.setProperty("voice", voice.id)
                break

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name

        engine.save_to_file(text, tmp_path)
        engine.runAndWait()
        engine.stop()

        with open(tmp_path, "rb") as f:
            audio_bytes = f.read()
        os.unlink(tmp_path)
        return audio_bytes

    except Exception as e:
        logger.error(f"TTS synthesis error: {e}")
        return b""
