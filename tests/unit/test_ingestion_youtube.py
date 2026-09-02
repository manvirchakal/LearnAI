"""``download_audio`` against a mocked ``yt_dlp.YoutubeDL`` — the same
approach ``test_asr_and_tts.py`` uses for faster-whisper/Piper: exercise
the real wrapper's argument mapping and result shaping without a real
network download.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from learnai.services.ingestion.youtube import download_audio


async def test_download_audio_returns_title_and_mp3_path(tmp_path: Path) -> None:
    fake_ydl = MagicMock()
    fake_ydl.__enter__.return_value = fake_ydl
    fake_ydl.__exit__.return_value = False
    fake_ydl.extract_info.return_value = {"title": "Lecture 1: Limits", "id": "abc123"}

    with patch(
        "learnai.services.ingestion.youtube.yt_dlp.YoutubeDL", return_value=fake_ydl
    ) as ydl_cls:
        title, path = await download_audio("https://youtube.com/watch?v=abc123", tmp_path)

    assert title == "Lecture 1: Limits"
    assert path == tmp_path / "abc123.mp3"
    fake_ydl.extract_info.assert_called_once_with(
        "https://youtube.com/watch?v=abc123", download=True
    )
    call_kwargs = ydl_cls.call_args.args[0]
    assert call_kwargs["postprocessors"][0]["key"] == "FFmpegExtractAudio"


async def test_download_audio_falls_back_to_url_when_title_missing(tmp_path: Path) -> None:
    fake_ydl = MagicMock()
    fake_ydl.__enter__.return_value = fake_ydl
    fake_ydl.__exit__.return_value = False
    fake_ydl.extract_info.return_value = {"title": None, "id": "xyz789"}

    with patch("learnai.services.ingestion.youtube.yt_dlp.YoutubeDL", return_value=fake_ydl):
        title, _ = await download_audio("https://youtube.com/watch?v=xyz789", tmp_path)

    assert title == "https://youtube.com/watch?v=xyz789"
