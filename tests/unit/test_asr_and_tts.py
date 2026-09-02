"""``FasterWhisperASR``/``PiperTTS`` against mocked model classes — the
same approach ``test_anthropic_pdf_extractor.py`` uses for the SDK client:
exercise the real adapter's orchestration (lazy load-once, argument
mapping, result shaping) without a real model file or network access.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from learnai.errors import ValidationError
from learnai.services.asr import FasterWhisperASR
from learnai.services.tts import PiperTTS


def _segment(start: float, end: float, text: str) -> SimpleNamespace:
    return SimpleNamespace(start=start, end=end, text=text)


async def test_transcribe_maps_segments_and_loads_model_once(tmp_path: Path) -> None:
    fake_model = MagicMock()
    fake_model.transcribe.return_value = (
        [_segment(0.0, 2.5, " hello "), _segment(2.5, 5.0, " world ")],
        SimpleNamespace(language="en"),
    )

    with patch("learnai.services.asr.WhisperModel", return_value=fake_model) as model_cls:
        asr = FasterWhisperASR("distil-large-v3", "int8")
        first = await asr.transcribe(tmp_path / "audio.mp3")
        second = await asr.transcribe(tmp_path / "other.mp3")

    model_cls.assert_called_once_with("distil-large-v3", compute_type="int8")
    assert first.language == "en"
    assert [s.text for s in first.segments] == ["hello", "world"]  # stripped
    assert [s.start for s in first.segments] == [0.0, 2.5]
    assert second.language == "en"


async def test_synthesize_raises_for_unconfigured_language(tmp_path: Path) -> None:
    tts = PiperTTS(tmp_path, {"en-US": "en_US-lessac-medium.onnx"})

    with pytest.raises(ValidationError, match="no TTS voice"):
        await tts.synthesize("hi", language="xx-XX")


def _fake_synthesize_wav(text: str, wav_file: object, **_kwargs: object) -> None:
    wav_file.setnchannels(1)  # type: ignore[attr-defined]
    wav_file.setsampwidth(2)  # type: ignore[attr-defined]
    wav_file.setframerate(22050)  # type: ignore[attr-defined]
    wav_file.writeframes(b"\x00\x00")  # type: ignore[attr-defined]


async def test_synthesize_loads_voice_once_and_returns_wav_bytes(tmp_path: Path) -> None:
    fake_voice = MagicMock()
    fake_voice.synthesize_wav.side_effect = _fake_synthesize_wav

    with patch("learnai.services.tts.PiperVoice.load", return_value=fake_voice) as load:
        tts = PiperTTS(tmp_path, {"en-US": "en_US-lessac-medium.onnx"})
        first = await tts.synthesize("hello", language="en-US")
        second = await tts.synthesize("world", language="en-US")

    load.assert_called_once_with(str(tmp_path / "en_US-lessac-medium.onnx"))
    assert first.startswith(b"RIFF")
    assert second.startswith(b"RIFF")
