import re
import pdfplumber
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException
from sqlalchemy.orm import Session
from server.database import SessionLocal, engine, Base
from server import models, schemas
import os
import json  # Import JSON module
from tqdm import tqdm
from typing import List  # Add this line

# Drop all existing tables
#Base.metadata.drop_all(bind=engine)

# Recreate all tables
Base.metadata.create_all(bind=engine)


app = FastAPI()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/api/chapters/", response_model=List[schemas.Chapter])
def get_chapters(db: Session = Depends(get_db)):
    chapters = db.query(models.Chapter).all()
    # Ensure sections is always a dictionary
    return [schemas.Chapter(id=chapter.id, title=chapter.title, sections=json.loads(chapter.content) if chapter.content else {}) for chapter in chapters]



@app.post("/api/upload-textbook/")
async def upload_textbook(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if file.content_type != 'application/pdf':
        return {"error": "File format not supported."}

    # Open the PDF file and extract text
    with pdfplumber.open(file.file) as pdf:
        text = ""
        for page in tqdm(pdf.pages, desc="Processing PDF"):
            text += page.extract_text()

    # Break the text into chapters and sections
    chapters = extract_chapters(text)

    # Save the chapters and sections in the database
    for chapter_title, chapter_content in chapters.items():
        # Convert the dictionary to a JSON string
        chapter_content_json = json.dumps(chapter_content)

        # Save to the database
        chapter = models.Chapter(title=chapter_title, content=chapter_content_json)
        db.add(chapter)
        db.commit()
        db.refresh(chapter)

    return {"message": "Textbook uploaded and processed successfully."}



def extract_sections(chapter_content):
    # This regex pattern should be updated to match the format of sections in your PDF
    section_pattern = re.compile(r'Section\s+\d+\b.*', re.IGNORECASE)
    sections = re.split(section_pattern, chapter_content)

    section_dict = {}
    for index, section in enumerate(sections):
        if section.strip():
            section_title = section_pattern.search(chapter_content)
            if section_title:
                section_dict[section_title.group()] = section.strip()
            else:
                section_dict[f'Section_{index}'] = section.strip()
    return section_dict

def extract_chapters(text):
    chapter_pattern = re.compile(r'Chapter\s+\d+\b.*', re.IGNORECASE)
    sections = re.split(chapter_pattern, text)

    chapters = {}
    for index, section in enumerate(sections):
        if section.strip():
            chapter_title = chapter_pattern.search(text)
            if chapter_title:
                chapters[chapter_title.group()] = {'Section_0': section.strip()}
            else:
                chapters[f'Introduction_{index}'] = {'Section_0': section.strip()}
    return chapters
