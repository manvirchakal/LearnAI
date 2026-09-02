"""YouTube audio import via yt-dlp — downloads and extracts to mp3 via
yt-dlp's own ffmpeg postprocessor (a different mechanism than the direct-
upload path in ``services/ingestion/media.py``, which needs no ffmpeg at
all since faster-whisper decodes the raw upload itself).

Runs inside the ARQ worker only (``worker.tasks.import_youtube_task``) —
the download is blocking, slow, and network-bound, exactly the kind of
work the old design ran synchronously inside a request handler
(``server/main.py``'s ``/transcribe-youtube``) that this modernization
moves off the request path entirely.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import yt_dlp


def _download_sync(url: str, dest_dir: Path) -> tuple[str, Path]:
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": str(dest_dir / "%(id)s.%(ext)s"),
        "postprocessors": [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}
        ],
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        title: str = info.get("title") or url
        video_id: str = info["id"]
    return title, dest_dir / f"{video_id}.mp3"


async def download_audio(url: str, dest_dir: Path) -> tuple[str, Path]:
    """Downloads ``url``'s audio as an mp3 under ``dest_dir``, returning
    the video's title and the mp3's path."""
    return await asyncio.to_thread(_download_sync, url, dest_dir)
