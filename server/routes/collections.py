"""
Collections API — groups of book sections, transcripts, slides and notes that
are studied together, with the same study/game/chat endpoints as a section.

    POST   /collections                     {name, materials}
    GET    /collections                     user-created (?include_auto=true adds per-upload ones)
    GET    /collections/{id}
    PATCH  /collections/{id}                {name}
    DELETE /collections/{id}
    PUT    /collections/{id}/materials      replaces materials (drops generated study materials)
    GET    /collections/{id}/study          cached study materials (404 if none)
    POST   /collections/{id}/study          get-or-generate
    POST   /collections/{id}/study/stream   same, as SSE (token/stage/done/error)
    POST   /collections/{id}/game           regenerate game
    GET    /collections/{id}/chat           history
    POST   /collections/{id}/chat           send message
    POST   /collections/{id}/chat/stream    same, as an AI SDK UI message stream
"""
import logging
from typing import Dict

from fastapi import APIRouter, Body, Depends, HTTPException, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse

from agents.chat_agent import get_history, run_chat_agent, stream_chat_agent
from agents.content_agent import load_cached_materials, run_content_agent, run_game_agent, stream_content_agent
from core.dependencies import get_user_id
from models.study import ChatHistory, ChatRequest, ChatResponse, GameResponse, StudyMaterials, StudyRequest
from services.collection_service import (
    collection_sources,
    create_collection,
    delete_collection,
    get_collection,
    get_collection_content,
    list_user_collections,
    rename_collection,
    update_collection_materials,
)
from utils.prompt_utils import format_content_for_prompt
from utils.streaming_utils import SSE_HEADERS, sse
from utils.ui_stream import UI_STREAM_HEADERS, chat_ui_stream

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/collections", tags=["collections"])


@router.post("")
async def create_collection_endpoint(
    name: str = Body(...),
    materials: Dict = Body(...),
    user_id: str = Depends(get_user_id),
):
    try:
        return create_collection(name, materials, user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def list_collections_endpoint(include_auto: bool = False, user_id: str = Depends(get_user_id)):
    return list_user_collections(user_id, include_auto=include_auto)


@router.get("/{collection_id}")
async def get_collection_endpoint(collection_id: str, user_id: str = Depends(get_user_id)):
    try:
        return get_collection(collection_id, user_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Collection not found")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.patch("/{collection_id}")
async def rename_collection_endpoint(collection_id: str, name: str = Body(..., embed=True),
                                     user_id: str = Depends(get_user_id)):
    if not name.strip():
        raise HTTPException(status_code=400, detail="Name must not be empty")
    try:
        return rename_collection(collection_id, name.strip(), user_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Collection not found")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.delete("/{collection_id}", status_code=204)
async def delete_collection_endpoint(collection_id: str, user_id: str = Depends(get_user_id)):
    try:
        delete_collection(collection_id, user_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Collection not found")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    return Response(status_code=204)


@router.put("/{collection_id}/materials")
async def update_materials(
    collection_id: str,
    materials: Dict = Body(...),
    user_id: str = Depends(get_user_id),
):
    try:
        return update_collection_materials(collection_id, materials, user_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Collection not found")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Study + chat over a whole collection (same agents as book sections) ──────

def _collection_or_404(collection_id: str, user_id: str) -> dict:
    try:
        return get_collection(collection_id, user_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Collection not found")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


def _collection_text(collection_id: str, user_id: str) -> str:
    try:
        return format_content_for_prompt(get_collection_content(collection_id, user_id))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Collection not found")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/{collection_id}/study", response_model=StudyMaterials)
def cached_collection_study(collection_id: str, user_id: str = Depends(get_user_id)):
    _collection_or_404(collection_id, user_id)
    cached = load_cached_materials(user_id, "collections", collection_id)
    if not cached:
        raise HTTPException(status_code=404, detail="Study materials not generated yet")
    return cached


@router.post("/{collection_id}/study", response_model=StudyMaterials)
def study_collection(collection_id: str, body: StudyRequest = StudyRequest(),
                     user_id: str = Depends(get_user_id)):
    text = _collection_text(collection_id, user_id)
    try:
        return run_content_agent(text, user_id, scope="collections", unit_id=collection_id,
                                 force_regenerate=body.force_regenerate)
    except Exception as e:
        logger.exception("Collection study generation failed")
        raise HTTPException(status_code=502, detail=f"Generation failed: {e}")


@router.post("/{collection_id}/study/stream")
async def stream_collection_study(collection_id: str, body: StudyRequest = StudyRequest(),
                                  user_id: str = Depends(get_user_id)):
    text = await run_in_threadpool(_collection_text, collection_id, user_id)

    async def events():
        try:
            async for event, data in stream_content_agent(text, user_id, scope="collections", unit_id=collection_id,
                                                          force_regenerate=body.force_regenerate):
                yield sse(event, data)
        except Exception as e:
            logger.exception("Streaming collection study failed")
            yield sse("error", f"Generation failed: {e}")

    return StreamingResponse(events(), media_type="text/event-stream", headers=SSE_HEADERS)


@router.post("/{collection_id}/game", response_model=GameResponse)
def regenerate_collection_game(collection_id: str, user_id: str = Depends(get_user_id)):
    text = _collection_text(collection_id, user_id)
    try:
        return {"game_code": run_game_agent(text, user_id, scope="collections", unit_id=collection_id,
                                            new_idea=True)}
    except LookupError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.exception("Collection game generation failed")
        raise HTTPException(status_code=502, detail=f"Generation failed: {e}")


@router.get("/{collection_id}/chat", response_model=ChatHistory)
def collection_chat_history(collection_id: str, user_id: str = Depends(get_user_id)):
    _collection_or_404(collection_id, user_id)
    return {"history": get_history(user_id, "collections", collection_id)}


@router.post("/{collection_id}/chat", response_model=ChatResponse)
def collection_chat(collection_id: str, body: ChatRequest, user_id: str = Depends(get_user_id)):
    _collection_text(collection_id, user_id)  # 404/403s, and indexes its sections for the tutor
    try:
        return run_chat_agent(body.message, collection_sources(collection_id, user_id), user_id, scope="collections",
                              unit_id=collection_id, language=body.language)
    except Exception as e:
        logger.exception("Collection chat failed")
        raise HTTPException(status_code=502, detail=f"Chat failed: {e}")


@router.post("/{collection_id}/chat/stream")
async def stream_collection_chat(collection_id: str, body: ChatRequest, user_id: str = Depends(get_user_id)):
    await run_in_threadpool(_collection_text, collection_id, user_id)  # as in collection_chat
    sources = await run_in_threadpool(collection_sources, collection_id, user_id)
    events = stream_chat_agent(body.message, sources, user_id, scope="collections", unit_id=collection_id,
                               language=body.language)
    return StreamingResponse(chat_ui_stream(events, logger), media_type="text/event-stream",
                             headers=UI_STREAM_HEADERS)
