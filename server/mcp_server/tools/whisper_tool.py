"""MCP tool: local Whisper transcription via faster-whisper."""
from fastmcp import FastMCP
from services.media_service import _transcribe_file

mcp = FastMCP("whisper")


@mcp.tool()
def transcribe_audio_file(audio_path: str) -> str:
    """Transcribe an audio file using local faster-whisper."""
    return _transcribe_file(audio_path)
