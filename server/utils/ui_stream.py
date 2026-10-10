"""
Vercel AI SDK UI message stream protocol (v1), so the web client's useChat can
consume the backend directly: SSE frames of JSON chunks, ending with [DONE].
https://ai-sdk.dev/docs/ai-sdk-ui/stream-protocol
"""
import json
import logging
import uuid
from typing import Any, AsyncIterator, Tuple

from utils.streaming_utils import SSE_HEADERS

UI_STREAM_HEADERS = {**SSE_HEADERS, "x-vercel-ai-ui-message-stream": "v1"}


def ui_chunk(chunk_type: str, **fields: Any) -> str:
    return f"data: {json.dumps({'type': chunk_type, **fields})}\n\n"


def ui_data(name: str, data: Any, transient: bool = True) -> str:
    """A custom data-<name> part; transient parts reach onData but aren't kept on the message."""
    return ui_chunk(f"data-{name}", data=data, transient=transient)


UI_DONE = "data: [DONE]\n\n"


async def chat_ui_stream(events: AsyncIterator[Tuple[str, str]], logger: logging.Logger) -> AsyncIterator[str]:
    """
    Turn ("stage", node) / ("token", text) events from a chat agent into one
    assistant message: stages become transient data-stage parts (progress
    labels), tokens become a single text part.
    """
    text_id = f"text-{uuid.uuid4().hex}"
    started = False
    yield ui_chunk("start")
    try:
        async for event, value in events:
            if event == "stage":
                yield ui_data("stage", value)
            elif event == "token" and value:
                if not started:
                    yield ui_chunk("text-start", id=text_id)
                    started = True
                yield ui_chunk("text-delta", id=text_id, delta=value)
        if started:
            yield ui_chunk("text-end", id=text_id)
        yield ui_chunk("finish")
    except Exception as e:
        logger.exception("Streaming chat failed")
        yield ui_chunk("error", errorText=f"Chat failed: {e}")
    yield UI_DONE
