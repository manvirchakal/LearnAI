"""Server-Sent Events formatting."""
import json
from typing import Any


def sse(event: str, data: Any) -> str:
    """One SSE frame. Data is JSON-encoded so newlines in tokens survive framing."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"
