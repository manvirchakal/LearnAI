from pydantic import BaseModel
from typing import List, Dict, Any

class UserBase(BaseModel):
    name: str
    email: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int

    class Config:
        from_attributes = True  # Use this instead of orm_mode

class Section(BaseModel):
    id: int
    title: str
    content: str

    class Config:
        orm_mode = True

class ChapterBase(BaseModel):
    title: str

class ChapterCreate(ChapterBase):
    content: Dict[str, Any]

class Chapter(ChapterBase):
    id: int
    sections: Dict[str, str]

    class Config:
        orm_mode = True
        from_attributes = True

    @classmethod
    def from_orm(cls, obj):
        # Override the default ORM conversion to include sections
        return cls(id=obj.id, title=obj.title, sections=json.loads(obj.content))


