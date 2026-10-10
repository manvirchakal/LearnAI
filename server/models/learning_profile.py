from pydantic import BaseModel
from typing import Dict, Optional


class ProfileAnswers(BaseModel):
    Visual: Dict[str, int] = {}
    Auditory: Dict[str, int] = {}
    ReadingWriting: Dict[str, int] = {}
    Kinesthetic: Dict[str, int] = {}


class LearningProfile(BaseModel):
    answers: Dict
    description: str = ""


class SaveProfileRequest(BaseModel):
    # {"Visual": {"<statement>": 1-5, ...}, "Auditory": {...}, ...}
    answers: Dict[str, Dict[str, int]]
