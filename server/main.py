import chardet
import os
import re
import logging 
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, WebSocket, WebSocketDisconnect, Request
from sqlalchemy.orm import Session
from server.database import SessionLocal, engine, Base
from server import models, schemas
import threading
from fastapi.responses import StreamingResponse
import json
import asyncio
from fastapi.middleware.cors import CORSMiddleware
import httpx
import tempfile
import subprocess
from fastapi.responses import FileResponse
import boto3
from botocore.exceptions import ClientError
from server import models
from functools import lru_cache

# Add AWS Bedrock client initialization
bedrock = boto3.client(
    service_name='bedrock-runtime',
    region_name='us-east-1'  # replace with your preferred region
)

# Create all tables in the database
Base.metadata.create_all(bind=engine)

# Initialize logging
logging.basicConfig(level=logging.DEBUG)

app = FastAPI()

# Allow your frontend origin
origins = [
    "http://localhost:3000",  # React frontend origin
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def index_content(db: Session):
    bucket_name = os.environ.get('BUCKET_NAME')
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    textbooks = db.query(models.Textbook).all()
    for textbook in textbooks:
        for chapter in textbook.chapters:
            blob = bucket.blob(f"chapter_{chapter.id}.txt")
            content = f"""
            Title: {chapter.title}
            Textbook: {textbook.title}
            Content: {chapter.content}
            """
            blob.upload_from_string(content, content_type="text/plain")

    # After uploading all documents, you might need to use a different API call
    # to trigger indexing, depending on the supported methods for your datastore

@app.post("/index-content")
async def index_content_endpoint(db: Session = Depends(get_db)):
    index_content(db)
    return {"message": "Content indexed successfully"}


def extract_chapters_and_sections_from_tex(tex_content: str):
    # Updated Chapter pattern with more flexibility
    chapter_pattern = re.compile(r'\\Chapter(\[.*?\])?\s*\n*\{([IVXLCDM]+)\}\s*\{(.+?)\}\n*', re.MULTILINE)

    # Section pattern remains the same but with added flexibility for spacing
    section_pattern = re.compile(r'\\Section(\[.*?\])?\s*\{(.+?)\}', re.MULTILINE)

    # Debug: log content length and first 500 chars to ensure content is being processed
    logging.debug(f"Processing TeX content of length {len(tex_content)}. First 500 chars:\n{tex_content[:500]}")
    
    # Split chapters
    chapters = re.split(chapter_pattern, tex_content)
    
    result = []
    
    logging.debug(f"Number of chapters found: {len(chapters)//3}")
    
    for i in range(1, len(chapters), 4):
        title = chapters[i + 2].strip()  # Chapter title
        content = chapters[i + 3].strip()  # Chapter content
        
        logging.debug(f"Processing Chapter: {title}. Content length: {len(content)}")

        # Find sections within each chapter
        sections = re.split(section_pattern, content)
        chapter_data = {"title": title, "content": sections[0].strip(), "sections": []}

        logging.debug(f"Number of sections found: {len(sections)//3}")

        for j in range(1, len(sections), 3):
            section_title = sections[j + 1].strip()  # Section title
            section_content = sections[j + 2].strip()  # Section content
            chapter_data["sections"].append({"title": section_title, "content": section_content})
            
            logging.debug(f"Added Section: {section_title}. Content length: {len(section_content)}")

        result.append(chapter_data)

    return result

@app.post("/upload")
async def upload_texbook(file: UploadFile = File(...), db: Session = Depends(get_db)):
    # Check if the file has a .tex extension
    if not file.filename.endswith('.tex'):
        raise HTTPException(status_code=400, detail="File format not supported. Please upload a TeX file.")
    
    content = await file.read()
    
    # Debug: log file size
    logging.debug(f"Uploaded file: {file.filename}, size: {len(content)} bytes")

    # Detect file encoding using chardet
    result = chardet.detect(content)
    encoding = result['encoding']

    try:
        content_str = content.decode(encoding)
        # Debug: log successful decoding
        logging.debug(f"File decoded successfully using {encoding} encoding.")
    except UnicodeDecodeError:
        logging.error("File encoding not supported.")
        raise HTTPException(status_code=400, detail="File encoding not supported.")

    # Extract chapters and sections
    chapters = extract_chapters_and_sections_from_tex(content_str)

    # Save the textbook
    textbook = models.Textbook(title="Some Title", description="Description of the textbook")
    db.add(textbook)
    db.commit()
    db.refresh(textbook)

    # Debug: log chapters being saved
    logging.debug(f"Saving textbook with {len(chapters)} chapters.")

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
    logging.debug("Textbook and chapters with sections uploaded successfully.")
    return {"message": "Textbook and chapters with sections uploaded successfully"}

def remove_latex_commands(text: str) -> str:
    """
    Prepare LaTeX commands for rendering in the browser.
    """
    # Replace display math environments
    text = re.sub(r'\\begin\{equation\}(.*?)\\end\{equation\}', r'$$\1$$', text, flags=re.DOTALL)
    text = re.sub(r'\\\[(.*?)\\\]', r'$$\1$$', text, flags=re.DOTALL)
    
    # Replace inline math environments
    text = re.sub(r'\\\((.*?)\\\)', r'$\1$', text)
    text = re.sub(r'\$\$(.*?)\$\$', r'$$\1$$', text)
    
    # Replace \efrac with \frac
    text = re.sub(r'\\efrac', r'\\frac', text)
    
    # Replace \DPtypo{wrong}{right} with right
    text = re.sub(r'\\DPtypo\{.*?\}\{(.*?)\}', r'\1', text)
    
    # Remove other LaTeX commands that MathJax doesn't need
    text = re.sub(r'\\(chapter|section|subsection|paragraph)\*?(\[.*?\])?\{(.*?)\}', r'\3', text)
    
    # Replace \Pagelabel, \DPPageSep, etc. with nothing
    text = re.sub(r'\\(Pagelabel|DPPageSep|Pageref|BindMath)(\{.*?\})+', '', text)
    
    # Replace \emph{text} with *text*
    text = re.sub(r'\\emph\{(.*?)\}', r'*\1*', text)
    
    return text.strip()

def build_endpoint_url(
    region: str,
    project_id: str,
    model_name: str,
    model_version: str,
    streaming: bool = False,
):
    base_url = f"https://{region}-aiplatform.googleapis.com/v1/"
    project_fragment = f"projects/{project_id}"
    location_fragment = f"locations/{region}"
    specifier = "streamRawPredict" if streaming else "rawPredict"
    model_fragment = f"publishers/mistralai/models/{model_name}@{model_version}"
    url = f"{base_url}{'/'.join([project_fragment, location_fragment, model_fragment])}:{specifier}"
    
    logging.info(f"Built URL: {url}")
    logging.info(f"Project ID: {project_id}")
    logging.info(f"Region: {region}")
    
    return url

def generate_narrative(chapter_content: str, chapter_id: int, db: Session):
    cleaned_text = remove_latex_commands(chapter_content)

    prompt = f"""Continue the explanation of key concepts from the following chapter content. For each concept:
    1. Define it clearly
    2. Provide a real-world analogy
    3. Give at least two practical examples
    4. Explain how it relates to other concepts in the chapter
    5. Discuss its importance or applications

    Use clear, engaging language suitable for a student new to these concepts. 
    Use LaTeX formatting for mathematical equations. Enclose LaTeX expressions in dollar signs for inline equations ($...$) and double dollar signs for display equations ($$...$$).

    Chapter content: {cleaned_text}

    Now, give an engaging explanation of the chapter's key concepts, with clear, detailed analogies and practical examples:"""

    full_response = ""
    for i in range(1):
        try:
            native_request = {
                'anthropic_version': 'bedrock-2023-05-31',
                'max_tokens': 4096,
                'temperature': 0.7,
                'top_p': 0.9,
                'messages': [
                    {
                        'role': 'user',
                        'content': [{'type': 'text', 'text': prompt}],
                    }
                ],
            }

            request = json.dumps(native_request)

            response = bedrock.invoke_model_with_response_stream(
                modelId="anthropic.claude-3-haiku-20240307-v1:0",
                body=request
            )

            for event in response['body']:
                chunk = json.loads(event['chunk']['bytes'])
                if chunk['type'] == 'content_block_delta':
                    full_response += chunk['delta'].get('text', '')

            if full_response.endswith(".") and len(full_response) < 4096 * 0.9:
                break

        except ClientError as e:
            logging.error(f"Error calling Bedrock: {e}")
            return f"Error: {str(e)}"

    # Store the generated narrative
    narrative_model = models.Narrative(chapter_id=chapter_id, content=full_response)
    db.add(narrative_model)
    db.commit()
    
    return full_response

@app.get("/generate-narrative/{chapter_id}")
async def generate_narrative_endpoint(chapter_id: int, db: Session = Depends(get_db)):
    chapter = db.query(models.Chapter).filter(models.Chapter.id == chapter_id).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    
    cleaned_chapter_content = remove_latex_commands(chapter.content)
    narrative = generate_narrative(cleaned_chapter_content, chapter_id, db)
    
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

    return {
        "id": chapter.id,
        "title": chapter.title,
        "content": chapter.content,
        "sections": [{"id": section.id, "title": section.title} for section in chapter.sections]
    }

@app.get("/textbooks/{textbook_id}/structure/")
async def get_textbook_structure(textbook_id: int, db: Session = Depends(get_db)):
    textbook = db.query(models.Textbook).filter(models.Textbook.id == textbook_id).first()
    
    if not textbook:
        raise HTTPException(status_code=404, detail="Textbook not found")
    
    chapters = db.query(models.Chapter).filter(models.Chapter.textbook_id == textbook_id).all()
    
    textbook_structure = []
    
    for chapter in chapters:
        sections = db.query(models.Section).filter(models.Section.chapter_id == chapter.id).all()
        section_data = [{"title": section.title, "id": section.id} for section in sections]
        
        chapter_data = {
            "id": chapter.id,
            "title": chapter.title,
            "sections": section_data
        }
        textbook_structure.append(chapter_data)
    
    return {
        "textbook_title": textbook.title,
        "chapters": textbook_structure
    }

@app.get("/check-chapters")
async def check_chapters(db: Session = Depends(get_db)):
    chapters = db.query(models.Chapter).all()
    return {"total_chapters": len(chapters), "chapters": [{"id": c.id, "title": c.title} for c in chapters]}

@app.get("/sections/{section_id}")
async def get_section(section_id: int, db: Session = Depends(get_db)):
    section = db.query(models.Section).filter(models.Section.id == section_id).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    return {
        "id": section.id,
        "title": section.title,
        "content": section.content,
        "chapter_id": section.chapter_id
    }

def generate_chat_response(prompt: str, chat_history: list, max_tokens: int = 500, max_history_tokens: int = 1000) -> str:
    full_response = ""
    
    try:
        # Prepare the chat history for the model
        formatted_history = []
        total_tokens = 0
        for msg in reversed(chat_history):
            role = "user" if msg['user'] == 'You' else "assistant"
            content = msg['text']
            message_tokens = len(content.split())  # Simple token count estimation
            if total_tokens + message_tokens > max_history_tokens:
                break
            formatted_history.insert(0, {"role": role, "content": content})
            total_tokens += message_tokens

        # Add the current prompt
        formatted_history.append({"role": "user", "content": prompt})

        native_request = {
            'anthropic_version': 'bedrock-2023-05-31',
            'max_tokens': max_tokens,
            'messages': formatted_history,
            'temperature': 0.7,
            'top_k': 250,
            'top_p': 1,
            'stop_sequences': ['\n\nHuman:'],
        }

        request = json.dumps(native_request)

        logging.debug(f"Sending request to Bedrock: {json.dumps(native_request, indent=2)}")

        response = bedrock.invoke_model_with_response_stream(
            modelId="anthropic.claude-3-haiku-20240307-v1:0",
            body=request
        )

        for event in response['body']:
            chunk = json.loads(event['chunk']['bytes'])
            if chunk['type'] == 'content_block_delta':
                full_response += chunk['delta'].get('text', '')

        return full_response.strip()

    except ClientError as e:
        logging.error(f"Error calling Bedrock: {e}")
        return f"Error: {str(e)}"

def get_stored_narrative(chapter_id: int, db: Session):
    narrative = db.query(models.Narrative).filter(models.Narrative.chapter_id == chapter_id).first()
    if narrative:
        return narrative.content
    return None

@app.post("/api/chat")
async def chat(request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()
        user_message = data.get('message')
        chapter_id = data.get('chapter_id')
        chat_history = data.get('chat_history', [])

        logging.info(f"Received chat request: message={user_message}, chapter_id={chapter_id}, chat_history_length={len(chat_history)}")

        if not user_message:
            raise HTTPException(status_code=400, detail="Message is required")

        if chapter_id is None:
            context = "You are an AI tutor. The student hasn't selected a specific chapter yet."
        else:
            # Fetch the stored narrative
            chapter_summary = get_stored_narrative(chapter_id, db)
            if chapter_summary is None:
                raise HTTPException(status_code=404, detail="Chapter summary not found")
            context = f"You are an AI tutor assisting a student with their studies. Here's a summary of the chapter they're studying:\n\n{chapter_summary}"

        prompt = f"""{context}

        Remember the context of the previous messages in this conversation. Here's the student's latest question:

        {user_message}

        Provide a helpful, accurate, and concise answer based on the given context, your general knowledge, and the conversation history. If the question is related to the chapter summary (if provided), make sure to reference it in your answer. If the question is not related to the provided context, politely guide the student back to the relevant material. Answer the question but be as concise as possible(4-6 sentences)."""

        # Generate AI response using the chat function
        ai_response = generate_chat_response(prompt, chat_history)

        # Update chat history
        chat_history.append({"user": "You", "text": user_message})
        chat_history.append({"user": "AI", "text": ai_response})

        return {"reply": ai_response, "updated_chat_history": chat_history}

    except Exception as e:
        logging.exception("Error in chat endpoint")
        raise HTTPException(status_code=500, detail=str(e))
