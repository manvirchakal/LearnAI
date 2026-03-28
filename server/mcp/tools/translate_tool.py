"""MCP tool: offline neural translation via argostranslate."""
from fastmcp import FastMCP
from services.accessibility_service import translate_text

mcp = FastMCP("translate")


@mcp.tool()
def translate(text: str, target_language: str) -> str:
    """Translate English text to the target language using argostranslate."""
    result = translate_text(text, target_language)
    return result or text   # fallback to original if translation fails
