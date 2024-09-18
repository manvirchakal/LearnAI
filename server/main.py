import chardet
import os
import re
import logging 
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from server.database import SessionLocal, engine, Base
from server import models, schemas
from google.cloud import aiplatform
import cv2
import threading
from fer import FER
from fastapi.responses import StreamingResponse
import json
import asyncio
from fastapi.middleware.cors import CORSMiddleware
import httpx
import google.auth
from google.auth.transport.requests import Request
import os
import json
import logging
import tempfile
import subprocess
from fastapi.responses import FileResponse
from google.cloud import discoveryengine
from google.cloud import aiplatform
from google.cloud import storage

import os

os.environ['GOOGLE_PROJECT_ID'] = 'the-program-434420-u3'
os.environ['GOOGLE_REGION'] = 'us-central1'
os.environ['BUCKET_NAME'] = 'learn-ai-bucket'
os.environ['DATASTORE_ID'] = 'learnairag_1726636747260'
os.environ['SEARCH_APP_ID'] = 'learnai_1726636706798'

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

# Initialize Vertex AI
aiplatform.init(project="the-program-434420-u3", location="us-central1")

# Initialize Vertex AI Search client
search_client = discoveryengine.SearchServiceClient()

# Initialize Vertex AI PaLM API
aiplatform.init(project="the-program-434420-u3", location="us-central1")

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

@app.post("/rag-query")
async def rag_query(query: str, db: Session = Depends(get_db)):
    # Step 1: Retrieve relevant documents
    search_engine_id = os.environ.get('DATASTORE_ID')
    search_app_id = os.environ.get('SEARCH_APP_ID')
    location = os.environ.get('GOOGLE_REGION')
    project_id = os.environ.get('GOOGLE_PROJECT_ID')

    parent = f"projects/{project_id}/locations/{location}/dataStores/{search_engine_id}/servingConfigs/{search_app_id}"

    request = discoveryengine.SearchRequest(
        parent=parent,
        query=query,
        page_size=5,
    )
    response = search_client.search(request)

    # Extract relevant content from search results
    relevant_content = []
    for result in response.results:
        relevant_content.append(result.document.struct_data["content"])

    # Step 2: Generate response using PaLM API
    model = "text-bison@001"
    prompt = f"""Based on the following information, answer the question: {query}

    Relevant information:
    {' '.join(relevant_content)}

    Answer:"""

    response = aiplatform.TextGenerationModel.from_pretrained(model).predict(prompt)

    return {"answer": response.text}

@app.get("/webcam_feed")
async def webcam_feed():
    global frame
    def generate():
        global frame
        while True:
            if frame is not None:
                resized_frame = cv2.resize(frame, (200, 150))  # Resize for viewport
                ret, jpeg = cv2.imencode('.jpg', resized_frame)
                frame_bytes = jpeg.tobytes()
                yield (b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    return StreamingResponse(generate(), media_type="multipart/x-mixed-replace; boundary=frame")

# WebSocket connection handler
@app.websocket("/ws/emotion")
async def emotion_websocket(websocket: WebSocket):
    logging.debug("WebSocket connection request received.")
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            logging.debug(f"Received from client: {data}")
            await websocket.send_text(f"Emotion received: {data}")
            logging.debug(f"Sent emotion confirmation to client: {data}")
    except WebSocketDisconnect:
        logging.info("WebSocket connection closed")
    except Exception as e:
        logging.error(f"Error in WebSocket connection: {e}")


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

def get_credentials():
    credentials, project_id = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    credentials.refresh(Request())
    return credentials.token

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

def generate_narrative(text: str, max_attempts=3, max_tokens=8192):
    model = "mistral-nemo"
    model_version = "2407"
    cleaned_text = remove_latex_commands(text)

    project_id = os.environ.get('GOOGLE_PROJECT_ID')
    region = os.environ.get('GOOGLE_REGION')
    url = build_endpoint_url(region, project_id, model, model_version)

    headers = {
        "Authorization": f"Bearer {get_credentials()}",
        "Accept": "application/json",
    }

    prompt_template = """
    Continue the explanation of key concepts from the following chapter content. For each concept:
    1. Define it clearly
    2. Provide a real-world analogy
    3. Give at least two practical examples
    4. Explain how it relates to other concepts in the chapter
    5. Discuss its importance or applications

    Use clear, engaging language suitable for a student new to these concepts. 
    Use LaTeX formatting for mathematical equations. Enclose LaTeX expressions in dollar signs for inline equations ($...$) and double dollar signs for display equations ($$...$$).

    If this is a continuation, pick up where the previous explanation left off.

    Chapter content: {content}

    Now, continue or start the detailed explanation:
    """

    full_response = ""
    for i in range(max_attempts):
        current_prompt = prompt_template.format(content=cleaned_text)
        if i > 0:
            current_prompt = "Continue from: " + full_response[-500:] + "\n" + current_prompt

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": current_prompt}],
            "stream": False,
        }

        with httpx.Client() as client:
            resp = client.post(url, json=payload, headers=headers, timeout=None)

        if resp.status_code == 200:
            try:
                response_data = resp.json()
                # Update this part to match the actual response structure
                generated_text = response_data['choices'][0]['message']['content']
                full_response += " " + generated_text

                # Check if the response seems complete
                if generated_text.endswith(".") and len(generated_text) < max_tokens * 0.9:
                    break
            except (json.JSONDecodeError, KeyError) as e:
                logging.error(f"Error parsing response: {e}")
                logging.debug(f"Response content: {resp.text}")  # Add this line for debugging
                return f"Error parsing response: {str(e)}"
        else:
            logging.error(f"API returned non-200 status code: {resp.status_code}")
            logging.debug(f"Response content: {resp.text}")  # Add this line for debugging
            return f"Error: API returned status code {resp.status_code}"

    return full_response

@app.get("/generate-narrative/{chapter_id}")
async def generate_narrative_endpoint(chapter_id: int, db: Session = Depends(get_db)):
    logging.info(f"Generating narrative for chapter_id: {chapter_id}")
    
    # Fetch the chapter content
    chapter = db.query(models.Chapter).filter(models.Chapter.id == chapter_id).first()
    if not chapter:
        logging.error(f"Chapter with id {chapter_id} not found")
        raise HTTPException(status_code=404, detail="Chapter not found")

    logging.info(f"Found chapter: {chapter.title}")

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

    try:
        narrative = generate_narrative(system_message)
        return {"narrative": narrative}
    except Exception as e:
        logging.exception("Error in generate_narrative")
        raise HTTPException(status_code=500, detail=str(e))

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
