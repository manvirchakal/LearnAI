from pydantic import BaseModel


class SynthesizeSpeechRequest(BaseModel):
    text: str
    language: str = "en-US"


class TranslateRequest(BaseModel):
    text: str
    target_language: str
