import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from core.dependencies import get_user_id
from core.llm import stream_llm_with_history
from models.ai_outputs import ChatRequest
from services.chat_service import send_message, get_chat_history
from utils.streaming_utils import text_stream_to_sse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])


@router.post("/api/chat")
async def chat(request: ChatRequest):
    try:
        reply = send_message(
            user_message=request.message,
            user_id=request.userId,
            file_id=request.fileId,
            section_name=request.sectionName,
            language=request.language,
            force_regenerate=request.forceRegenerate,
        )
        return {"reply": reply}
    except Exception as e:
        logger.exception("Error in chat endpoint")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat-history")
async def chat_history(
    file_id: str,
    section_name: str,
    user_id: str = Depends(get_user_id),
):
    return get_chat_history(user_id, file_id, section_name)
