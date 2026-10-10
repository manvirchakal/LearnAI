"""MCP tool: local TTS via pyttsx3."""
import base64
from fastmcp import FastMCP
from services.accessibility_service import synthesize_speech

mcp = FastMCP("tts")


@mcp.tool()
def synthesize(text: str, language: str = "en-US") -> str:
    """Synthesize speech and return base64-encoded WAV bytes."""
    audio_bytes = synthesize_speech(text, language)
    return base64.b64encode(audio_bytes).decode()
