"""In-memory ``ASREngine`` stand-in for tests — no real faster-whisper
model load or audio decoding, matching ``tests/fakes/extraction.py``'s
pattern (a pre-seeded response plus a call log).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from learnai.services.asr import TranscriptResult


@dataclass
class FakeASR:
    result: TranscriptResult | None = None
    calls: list[dict[str, Any]] = field(default_factory=list)

    async def transcribe(self, audio_path: Path) -> TranscriptResult:
        self.calls.append({"audio_path": str(audio_path)})
        assert self.result is not None, "FakeASR.result was not configured"
        return self.result
