import os
import re
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException
from sqlalchemy.orm import Session
from server.database import SessionLocal, engine, Base
from server import models, schemas

# Create all tables in the database
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Function to extract chapters from TeX file
def extract_chapters_from_tex(tex_content: str):
    # Regular expression to match both \Chapter{*number*} and \Chapter[description]{*number*}
    chapter_pattern = re.compile(r'\\Chapter(\[.*?\])?\{(.+?)\}', re.MULTILINE)
    chapters = re.split(chapter_pattern, tex_content)

    result = []
    for i in range(1, len(chapters), 3):
        # If there's a description in square brackets, we skip it and focus on the chapter title
        title = chapters[i+1].strip()  # Chapter title
        content = chapters[i+2].strip()  # Chapter content
        result.append((title, content))

    return result

@app.post("/upload")
async def upload_texbook(file: UploadFile = File(...), db: Session = Depends(get_db)):
    # Ensure it's a TeX file
    if not file.filename.endswith(".tex"):
        raise HTTPException(status_code=400, detail="File format not supported. Please upload a TeX file.")
    
    try:
        # Attempt to read the file as UTF-8
        content = await file.read()
        content_str = content.decode('utf-8')
    except UnicodeDecodeError:
        # If UTF-8 decoding fails, try with latin-1 as fallback
        content_str = content.decode('latin-1')

    # Extract chapters from the TeX content
    chapters = extract_chapters_from_tex(content_str)

    # Save the textbook and chapters
    textbook = models.Textbook(title="Some Title", description="Description of the textbook")
    db.add(textbook)
    db.commit()
    db.refresh(textbook)

    for title, chapter_content in chapters:
        chapter = models.Chapter(title=title, content=chapter_content, textbook_id=textbook.id)
        db.add(chapter)
    
    db.commit()

    return {"message": "Textbook and chapters uploaded successfully"}


# Endpoint to get all textbooks
@app.get("/textbooks/")
async def get_textbooks(db: Session = Depends(get_db)):
    textbooks = db.query(models.Textbook).all()
    return textbooks

# Endpoint to get chapters of a specific textbook by textbook ID
@app.get("/textbooks/{textbook_id}/chapters/")
async def get_chapters(textbook_id: int, db: Session = Depends(get_db)):
    chapters = db.query(models.Chapter).filter(models.Chapter.textbook_id == textbook_id).all()
    
    if not chapters:
        raise HTTPException(status_code=404, detail="No chapters found for this textbook.")
    
    return chapters

# Endpoint to view individual chapter by chapter_id
@app.get("/chapters/{chapter_id}/")
async def get_chapter(chapter_id: int, db: Session = Depends(get_db)):
    chapter = db.query(models.Chapter).filter(models.Chapter.id == chapter_id).first()
    
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found.")
    
    return chapter
