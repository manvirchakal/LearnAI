from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class StudyRequest(BaseModel):
    force_regenerate: bool = False


class StudyMaterials(BaseModel):
    narrative: str
    game_idea: str
    game_code: str
    diagrams: List[str]
    game_version: int = 0


class GameResponse(BaseModel):
    game_code: str
    game_version: int = 0


class GameFixRequest(BaseModel):
    """An error the browser hit running a game, reported by the game sandbox."""
    error: str = Field(max_length=4000)
    version: int                    # the game_version that broke
    line: Optional[int] = None      # line in the game code, if the stack named one
    phase: Optional[Literal["compile", "render", "runtime", "promise"]] = None
    stack: Optional[str] = Field(None, max_length=8000)


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
