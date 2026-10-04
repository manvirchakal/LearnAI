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

def _language_pair(source: str, target: str):
    from argostranslate import translate
    langs = {l.code: l for l in translate.get_installed_languages()}
    return langs.get(source), langs.get(target)


def translate_text(text: str, target_language: str, source_language: str = "en") -> Optional[str]:
    """
    Translate text offline with argostranslate.
    The language pair's model is downloaded once, on first use.
    """
    if source_language == target_language:
        return text
    try:
        from argostranslate import package
        from_lang, to_lang = _language_pair(source_language, target_language)
        if not from_lang or not to_lang:
            logger.info(f"Installing argostranslate package {source_language}→{target_language}")
            package.update_package_index()
            pkg = next((p for p in package.get_available_packages()
                        if p.from_code == source_language and p.to_code == target_language), None)
            if not pkg:
                logger.warning(f"No argostranslate package for {source_language}→{target_language}")
                return None
            package.install_from_path(pkg.download())
            from_lang, to_lang = _language_pair(source_language, target_language)
        if not from_lang or not to_lang:
            return None
        return from_lang.get_translation(to_lang).translate(text)
    except Exception as e:
        logger.error(f"Translation error ({source_language}→{target_language}): {e}")
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
