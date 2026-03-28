import logging
from fastapi import APIRouter, Body, Depends, HTTPException
from typing import Dict

from core.dependencies import get_user_id
from services.collection_service import (
    create_collection,
    get_collection,
    list_user_collections,
    update_collection_materials,
)

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
