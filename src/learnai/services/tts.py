"""Local text-to-speech via Piper (ONNX, CPU) — the Polly replacement.
Same lazy-load-on-first-call, thread-offloaded pattern as
``services/asr.py``'s ``FasterWhisperASR`` and ``FastEmbedEmbedder`` —
model load is expensive and must happen once, not eagerly at process
startup (would risk failing it) and not inline (would block the event
loop the caller runs on).

Unlike ASR, this is called from the API process directly (synthesis is
fast enough, and free, to run inline in a request handler rather than
needing a job/poll round trip) — see ``routers/media.py``.
"""

from __future__ import annotations

import asyncio
import io
import wave
from pathlib import Path
from typing import Protocol

from piper import PiperVoice

from learnai.errors import ValidationError


class TTSEngine(Protocol):
    async def synthesize(self, text: str, *, language: str) -> bytes: ...


class PiperTTS:
    def __init__(self, voice_dir: Path, voice_map: dict[str, str]) -> None:
        self._voice_dir = voice_dir
        self._voice_map = voice_map
        self._voices: dict[str, PiperVoice] = {}

    async def synthesize(self, text: str, *, language: str) -> bytes:
        return await asyncio.to_thread(self._synthesize_sync, text, language)

    def _synthesize_sync(self, text: str, language: str) -> bytes:
        voice_file = self._voice_map.get(language)
        if voice_file is None:
            raise ValidationError(f"no TTS voice configured for language {language!r}")

        voice = self._voices.get(language)
        if voice is None:
            voice = PiperVoice.load(str(self._voice_dir / voice_file))
            self._voices[language] = voice

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            voice.synthesize_wav(text, wav_file)
        return buffer.getvalue()
