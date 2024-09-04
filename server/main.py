import chardet
import os
import re
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException
from sqlalchemy.orm import Session
from server.database import SessionLocal, engine, Base
from server import models, schemas
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
import torch

# Create all tables in the database
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Load Llama 3.1 8B with 4-bit quantization
model_name = "meta-llama/Meta-Llama-3.1-8B-Instruct"

# Initialize quantization config for 4-bit
quantization_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16,  # Changed to fp16 for performance
    llm_int8_enable_fp32_cpu_offload=True  # Enable fp32 offload for larger models
)

# Load the tokenizer and model with quantization config
tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=False)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    device_map="auto",
    quantization_config=quantization_config
)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def extract_chapters_and_sections_from_tex(tex_content: str):
    # Regular expression to match chapters (\Chapter{*number*} or \Chapter[description]{*number*})
    chapter_pattern = re.compile(r'\\Chapter(\[.*?\])?\{(.+?)\}', re.MULTILINE)
    # Regular expression to match sections (\Section[]{} or \Section{})
    section_pattern = re.compile(r'\\Section(\[.*?\])?\{(.+?)\}', re.MULTILINE)

    chapters = re.split(chapter_pattern, tex_content)
    result = []

    for i in range(1, len(chapters), 3):
        title = chapters[i + 1].strip()  # Chapter title
        content = chapters[i + 2].strip()  # Chapter content

        # Find sections within each chapter
        sections = re.split(section_pattern, content)
        chapter_data = {"title": title, "content": sections[0].strip(), "sections": []}

        for j in range(1, len(sections), 3):
            section_title = sections[j + 1].strip()  # Section title
            section_content = sections[j + 2].strip()  # Section content
            chapter_data["sections"].append({"title": section_title, "content": section_content})

        result.append(chapter_data)

    return result

@app.post("/upload")
async def upload_texbook(file: UploadFile = File(...), db: Session = Depends(get_db)):
    # Check if the file has a .tex extension
    if not file.filename.endswith('.tex'):
        raise HTTPException(status_code=400, detail="File format not supported. Please upload a TeX file.")
    
    content = await file.read()

    # Detect file encoding using chardet
    result = chardet.detect(content)
    encoding = result['encoding']

    try:
        content_str = content.decode(encoding)
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File encoding not supported.")

    # Extract chapters and sections
    chapters = extract_chapters_and_sections_from_tex(content_str)

    # Save the textbook
    textbook = models.Textbook(title="Some Title", description="Description of the textbook")
    db.add(textbook)
    db.commit()
    db.refresh(textbook)

    for chapter_data in chapters:
        chapter = models.Chapter(title=chapter_data['title'], content=chapter_data['content'], textbook_id=textbook.id)
        db.add(chapter)
        db.commit()
        db.refresh(chapter)

        # Save sections for each chapter
        for section_data in chapter_data['sections']:
            section = models.Section(title=section_data['title'], content=section_data['content'], chapter_id=chapter.id)
            db.add(section)

    db.commit()
    return {"message": "Textbook and chapters with sections uploaded successfully"}

def remove_latex_commands(text: str) -> str:
    """
    Remove common LaTeX commands and symbols from the text.
    """
    # Remove LaTeX commands
    cleaned_text = re.sub(r"\\[a-zA-Z]+(\[.*?\])?(\{.*?\})?", "", text)
    # Remove curly braces and percent signs
    cleaned_text = re.sub(r"[{}%]", "", cleaned_text)
    return cleaned_text.strip()


def generate_narrative(text: str):
    # Preprocess the text to remove LaTeX commands
    cleaned_text = remove_latex_commands(text)

    # Set pad_token to eos_token if it's not already set
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    inputs = tokenizer(cleaned_text, return_tensors="pt", padding=True).to("cuda")
    input_ids = inputs["input_ids"]
    attention_mask = inputs["attention_mask"]

    # Generate response with a higher token limit and lower temperature
    output_tokens = model.generate(
        input_ids=input_ids,
        attention_mask=attention_mask,
        max_new_tokens=4000,  # Increased to allow for more detailed outputs
        temperature=0.3,  # Lowered to make explanations more consistent and focused
        repetition_penalty=1.1,  # Reduced to allow for more depth in the explanation
    )

    # Decode the output
    generated_text = tokenizer.decode(output_tokens[0], skip_special_tokens=True)

    print(generated_text)

    return generated_text


@app.get("/generate-narrative/{chapter_id}")
async def generate_narrative_endpoint(chapter_id: int, db: Session = Depends(get_db)):
    # Fetch the chapter content
    chapter = db.query(models.Chapter).filter(models.Chapter.id == chapter_id).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    # Clean the LaTeX content before sending it to the model
    cleaned_chapter_content = remove_latex_commands(chapter.content)

    system_message = (
        f"Act as an experienced teacher who wants to make complex topics simple and interesting. List out and explain the key concepts from the following chapter with clear analogies and relatable examples. "
        f"Use varied, real-world scenarios to demonstrate how each concept works in practical situations. Provide detailed explanations that uncover different aspects of the material, and don't hesitate to go deep into each idea. "
        f"Instead of summarizing, imagine you are guiding the learner through each concept with patience, ensuring they grasp not just the 'what' but also the 'why' behind the material.\n\n"
        f"Chapter content: {cleaned_chapter_content}\n"
        f"---\n"
        f"Now, give an engaging explanation of the chapter's key concepts, with clear, detailed analogies and practical examples:"
    )

    # Generate the narrative using the updated message
    narrative = generate_narrative(system_message)

    return {"narrative": narrative}

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

@app.get("/chapters/{chapter_id}")
async def get_chapter(chapter_id: int, db: Session = Depends(get_db)):
    chapter = db.query(models.Chapter).filter(models.Chapter.id == chapter_id).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    # Get associated sections
    sections = db.query(models.Section).filter(models.Section.chapter_id == chapter_id).all()

    return {
        "id": chapter.id,
        "title": chapter.title,
        "content": chapter.content,
        "sections": [{"id": section.id, "title": section.title, "content": section.content} for section in sections]
    }
