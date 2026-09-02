"""In-memory ``TTSEngine`` stand-in for tests — no real Piper voice load
or synthesis, matching ``tests/fakes/asr.py``'s pattern.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from learnai.errors import ValidationError


@dataclass
class FakeTTS:
    audio_bytes: bytes = b"fake-wav-bytes"
    supported_languages: set[str] = field(default_factory=lambda: {"en-US"})
    calls: list[dict[str, Any]] = field(default_factory=list)

    async def synthesize(self, text: str, *, language: str) -> bytes:
        self.calls.append({"text": text, "language": language})
        if language not in self.supported_languages:
            raise ValidationError(f"no TTS voice configured for language {language!r}")
        return self.audio_bytes
