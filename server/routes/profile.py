from fastapi import APIRouter, Depends, HTTPException
from core.dependencies import get_user_id
from services.profile_service import save_learning_profile, get_full_learning_profile
from models.ai_outputs import SaveProfileRequest

router = APIRouter(prefix="/profile", tags=["profile"])


@router.post("/save-learning-profile")
async def save_profile(profile: dict, user_id: str = Depends(get_user_id)):
    try:
        return save_learning_profile(user_id, profile.get("answers", profile))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/learning-profile")
async def get_profile(user_id: str = Depends(get_user_id)):
    data = get_full_learning_profile(user_id)
    if not data:
        raise HTTPException(status_code=404, detail="Learning profile not found")
    return data
