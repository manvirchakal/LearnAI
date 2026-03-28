from pydantic import BaseModel
from typing import List, Optional


class Section(BaseModel):
    title: str
    page: int


class Chapter(BaseModel):
    number: str
    title: str
    page: int
    sections: List[Section] = []


class TextbookMetadata(BaseModel):
    title: str
    s3_key: str = ""          # kept for backward compat; maps to local path
    local_key: str = ""
    user_id: str
    document_type: str
    table_of_contents: List[Chapter] = []
