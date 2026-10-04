import logging
from fastapi import APIRouter, Body, Depends, HTTPException
from typing import Dict

from agents.chat_agent import get_history, run_chat_agent
from agents.content_agent import run_content_agent
from core.dependencies import get_user_id
from models.study import ChatHistory, ChatRequest, ChatResponse, StudyMaterials, StudyRequest
from services.collection_service import (
    create_collection,
    get_collection,
    get_collection_content,
    list_user_collections,
    update_collection_materials,
)
from utils.prompt_utils import format_content_for_prompt

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
async def list_collections_endpoint(user_id: str = Depends(get_user_id)):
    return list_user_collections(user_id)


@router.get("/{collection_id}")
async def get_collection_endpoint(collection_id: str, user_id: str = Depends(get_user_id)):
    try:
        return get_collection(collection_id, user_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Collection not found")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


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

def _collection_text(collection_id: str, user_id: str) -> str:
    try:
        return format_content_for_prompt(get_collection_content(collection_id, user_id))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Collection not found")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


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


@router.get("/{collection_id}/chat", response_model=ChatHistory)
def collection_chat_history(collection_id: str, user_id: str = Depends(get_user_id)):
    return {"history": get_history(user_id, "collections", collection_id)}


@router.post("/{collection_id}/chat", response_model=ChatResponse)
def collection_chat(collection_id: str, body: ChatRequest, user_id: str = Depends(get_user_id)):
    text = _collection_text(collection_id, user_id)
    try:
        return run_chat_agent(body.message, text, user_id, scope="collections",
                              unit_id=collection_id, language=body.language)
    except Exception as e:
        logger.exception("Collection chat failed")
        raise HTTPException(status_code=502, detail=f"Chat failed: {e}")
