from pydantic import BaseModel
from typing import List, Optional, Dict


class NarrativeResult(BaseModel):
    narrative: str
    game_idea: str
    game_code: str
    diagrams: List[str]


class GameIdeaRequest(BaseModel):
    game_idea: str


class ChatMessage(BaseModel):
    user: str        # "You" | "AI"
    text: str


class ChatRequest(BaseModel):
    message: str
    userId: str
    fileId: str
    sectionName: str
    language: str = "en"
    forceRegenerate: str = "false"


class GenerateNarrativeRequest(BaseModel):
    chapter_content: str = ""
    user_id: str = ""
    file_id: str = ""
    section_id: str = ""
    force_regenerate: bool = False


class SynthesizeSpeechRequest(BaseModel):
    text: str
    language: str = "en-US"


class TranslateRequest(BaseModel):
    text: str
    target_language: str
