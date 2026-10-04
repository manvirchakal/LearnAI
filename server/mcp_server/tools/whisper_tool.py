"""MCP tool: local Whisper transcription via faster-whisper."""
from fastmcp import FastMCP

from core import storage
from services.media_service import transcribe_file

mcp = FastMCP("whisper")


@mcp.tool()
def transcribe_stored_audio(key: str) -> str:
    """Transcribe an audio/video file held in local storage (key relative to DATA_DIR)."""
    path = storage.get_local_path(key)
    if not path.is_file():
        raise FileNotFoundError(f"No stored file at {key}")
    return transcribe_file(path)
