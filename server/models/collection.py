from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime


class TextbookSectionRef(BaseModel):
    section_id: str
    title: str
    page: int
    local_key: str
    added_date: str = Field(default_factory=lambda: datetime.now().isoformat())


class CollectionMaterials(BaseModel):
    textbook_sections: List[Dict] = []
    transcriptions: List[Dict] = []
    presentations: List[Dict] = []
    notes: List[Dict] = []
    subcollections: List[str] = []


class Collection(BaseModel):
    collection_id: str
    name: str
    created_date: str = Field(default_factory=lambda: datetime.now().isoformat())
    user_id: str
    chapter_number: Optional[str] = None
    parent_chapter: Optional[str] = None
    materials: CollectionMaterials = Field(default_factory=CollectionMaterials)


class CreateCollectionRequest(BaseModel):
    name: str
    materials: Dict = {}
