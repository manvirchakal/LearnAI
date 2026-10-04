"""Server-Sent Events formatting."""
import json
from typing import Any

# no-transform stops gzip in intermediaries (including the Next.js proxy) from
# buffering the stream; X-Accel-Buffering does the same for nginx.
SSE_HEADERS = {"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"}


def sse(event: str, data: Any) -> str:
    """One SSE frame. Data is JSON-encoded so newlines in tokens survive framing."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"
