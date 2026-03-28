"""
Server-Sent Events (SSE) streaming utilities for FastAPI.
Wraps async generators from core/llm.py into SSE format.
"""
import json
import logging
from typing import AsyncGenerator

logger = logging.getLogger(__name__)


async def text_stream_to_sse(
    generator: AsyncGenerator[str, None],
    event: str = "message",
) -> AsyncGenerator[str, None]:
    """
    Convert an async text generator into SSE-formatted byte chunks.
    Usage:
        return StreamingResponse(text_stream_to_sse(stream), media_type="text/event-stream")
    """
    try:
        async for token in generator:
            data = json.dumps({"token": token})
            yield f"data: {data}\n\n"
        yield "data: [DONE]\n\n"
    except Exception as e:
        logger.error(f"Streaming error: {e}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


async def collect_stream(generator: AsyncGenerator[str, None]) -> str:
    """Collect all tokens from a streaming generator into a single string."""
    parts = []
    async for token in generator:
        parts.append(token)
    return "".join(parts)
