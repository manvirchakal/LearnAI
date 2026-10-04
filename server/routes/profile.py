"""
Learning profile API (VARK questionnaire).

    GET  /profile/questionnaire  statements per category, answered on a 1-5 scale
    GET  /profile                saved profile (404 if none)
    PUT  /profile                {answers: {Visual: {statement: score}, ...}} → profile
"""
from fastapi import APIRouter, Depends, HTTPException

from core.dependencies import get_user_id
from models.learning_profile import LearningProfile, SaveProfileRequest
from services.profile_service import get_full_learning_profile, save_learning_profile
from utils.prompt_utils import LEARNING_CATEGORIES

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/questionnaire")
def questionnaire():
    return {"scale": {"min": 1, "max": 5}, "categories": LEARNING_CATEGORIES}


@router.get("", response_model=LearningProfile)
def get_profile(user_id: str = Depends(get_user_id)):
    data = get_full_learning_profile(user_id)
    if not data:
        raise HTTPException(status_code=404, detail="Learning profile not found")
    return data


@router.put("", response_model=LearningProfile)
def save_profile(body: SaveProfileRequest, user_id: str = Depends(get_user_id)):
    try:
        save_learning_profile(user_id, body.answers)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not generate profile description: {e}")
    return get_full_learning_profile(user_id)
