"""Local speech-to-text via faster-whisper (CTranslate2) — the Transcribe
replacement. Runs entirely on-device, no AWS account, no per-minute cost.

``transcribe`` is async despite ``WhisperModel.transcribe`` being
synchronous: it's CPU-bound (not I/O), and a real transcription can take
tens of seconds to minutes, which would otherwise block the ARQ worker's
event loop for the whole run — pushed to a thread instead, the same
pattern ``FastEmbedEmbedder.embed`` uses for the same reason.

Model load is lazy (deferred to the first ``transcribe()`` call, not
``__init__``) for the same reason ``FastEmbedEmbedder`` defers its own
load: constructing this in worker startup must never be able to fail
process startup, and the model file itself may need a cold download.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Protocol

from faster_whisper import WhisperModel
from pydantic import BaseModel


class TranscriptSegment(BaseModel):
    start: float  # seconds
    end: float
    text: str


class TranscriptResult(BaseModel):
    language: str
    segments: list[TranscriptSegment]


class ASREngine(Protocol):
    async def transcribe(self, audio_path: Path) -> TranscriptResult: ...


class FasterWhisperASR:
    def __init__(self, model_size: str, compute_type: str) -> None:
        self._model_size = model_size
        self._compute_type = compute_type
        self._model: WhisperModel | None = None

    async def transcribe(self, audio_path: Path) -> TranscriptResult:
        return await asyncio.to_thread(self._transcribe_sync, audio_path)

    def _transcribe_sync(self, audio_path: Path) -> TranscriptResult:
        if self._model is None:
            self._model = WhisperModel(self._model_size, compute_type=self._compute_type)
        segments, info = self._model.transcribe(str(audio_path))
        collected = [
            TranscriptSegment(start=segment.start, end=segment.end, text=segment.text.strip())
            for segment in segments
        ]
        return TranscriptResult(language=info.language, segments=collected)
