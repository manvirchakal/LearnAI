from typing import List, Literal
from pydantic import BaseModel


class StudyRequest(BaseModel):
    force_regenerate: bool = False


class StudyMaterials(BaseModel):
    narrative: str
    game_idea: str
    game_code: str
    diagrams: List[str]


class GameResponse(BaseModel):
    game_code: str


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str
    language: str = "en"


class ChatHistory(BaseModel):
    history: List[ChatMessage]


class ChatResponse(ChatHistory):
    reply: str
