from typing import List
from pydantic import BaseModel


class Section(BaseModel):
    id: str            # stable, URL-safe: "ch3.s2"
    title: str
    start_page: int
    end_page: int


class Chapter(BaseModel):
    id: str            # "ch3"
    number: str
    title: str
    start_page: int
    end_page: int
    sections: List[Section]


class BookSummary(BaseModel):
    file_id: str
    title: str
    filename: str
    document_type: str
    num_pages: int
    chapter_count: int
    section_count: int
    uploaded_at: str = ""


class BookDetail(BookSummary):
    chapters: List[Chapter]
