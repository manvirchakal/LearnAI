import chardet
import os
import re
import logging 
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from server.database import SessionLocal, engine, Base
from server import models, schemas
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
import torch
from fastapi.middleware.cors import CORSMiddleware
import cv2
import threading
from fer import FER
from fastapi.responses import StreamingResponse
import json
import asyncio

from haystack.document_stores import InMemoryDocumentStore
from haystack.nodes import BM25Retriever, PromptNode
from haystack.pipelines import Pipeline


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

# Manage WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

# Emotion Detection using FER
emotion_detector = FER()
emotion_websocket = None  # Store the WebSocket globally

# Load Llama 3.1 8B with 4-bit quantization
# model_name = "meta-llama/Meta-Llama-3.1-8B-Instruct"

# Load Llama 3.1 8B with 4-bit quantization
model_name = "mistralai/Mistral-7B-Instruct-v0.3"

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

# Global variable to store the captured frame
frame = None

# Set up Haystack components
document_store = InMemoryDocumentStore()
retriever = BM25Retriever(document_store=document_store)


def capture_video():
    global frame, emotion_websocket
    cap = cv2.VideoCapture(0)  # Default webcam
    logging.info("Video capture started.")
    while True:
        ret, frame = cap.read()
        if not ret:
            logging.error("Failed to capture frame from webcam.")
            break

        # Emotion detection
        emotions = emotion_detector.detect_emotions(frame)
        if emotions:
            for face in emotions:
                logging.debug(f"Detected emotions: {face['emotions']}")
                
                dominant_emotion = max(face["emotions"], key=face["emotions"].get)
                confidence = face["emotions"][dominant_emotion]
                logging.debug(f"Dominant emotion: {dominant_emotion}, confidence: {confidence}")

                # Send "angry" emotion if confidence > 0.5
                if dominant_emotion == "angry" and confidence > 0.5:
                    emotion_data = json.dumps({"emotion": "angry"})
                    if emotion_websocket:
                        asyncio.run(manager.broadcast(emotion_data))
                        logging.info(f"Broadcasting emotion data: {emotion_data}")

        cv2.waitKey(10)
    cap.release()
    logging.info("Video capture stopped.")


# Start capturing video in a separate thread
thread = threading.Thread(target=capture_video, daemon=True)
thread.start()

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


# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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
    Remove common LaTeX commands and symbols from the text.
    """
    # Remove LaTeX commands
    cleaned_text = re.sub(r"\\[a-zA-Z]+(\[.*?\])?(\{.*?\})?", "", text)
    # Remove curly braces and percent signs
    cleaned_text = re.sub(r"[{}%]", "", cleaned_text)
    return cleaned_text.strip()


# Adding the other textbooks to the document store for RAG Purposes
#This function also adds the textbook which has the chapter we generate the narrative from as well so there might be slight redundant data
def add_textbooks_to_store(db: Session):
    textbooks = db.query(models.Textbook).all()
    documents = [{"content": remove_latex_commands(textbook.content)} for textbook in textbooks]
    document_store.write_documents(documents)

# Retrieve supplementary textbooks to use for RAG
def retrieve_supplementary_content(textbook_content: str, top_k=3):
    # Retrieve top-k relevant documents
    retrieved_docs = retriever.retrieve(query=textbook_content, top_k=top_k)
    supplementary_content = " ".join([doc.content for doc in retrieved_docs])
    return supplementary_content

def generate_narrative(text: str, supplementary_chapters: str):
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
        max_new_tokens=2000,  # Increased to allow for more detailed outputs
        temperature=0.9,  # Lowered to make explanations more consistent and focused
        repetition_penalty=1.0,  # Reduced to allow for more depth in the explanation
    )

    # Generate response with a higher token limit and lower temperature
    #output_tokens = model.generate(
    #    input_ids=input_ids,
    #    attention_mask=attention_mask,
    #    max_new_tokens=2000,  # Increased to allow for more detailed outputs
    #    temperature=0.9,  # Lowered to make explanations more consistent and focused
    #    repetition_penalty=1.0,  # Reduced to allow for more depth in the explanation
    #)

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

    # Retrieve supplementary content from other textbooks
    supplementary_content = retrieve_supplementary_content(cleaned_chapter_content)
    #Does this supplementary content need to cleaned of Latex Content as well?
    cleaned_supplementary_content = remove_latex_commands(supplementary_content)

    system_message = (
        f"Act as an experienced teacher who wants to make complex topics simple and interesting. List out and explain the key concepts from the following chapter with clear analogies and relatable examples. "
        f"Use varied, real-world scenarios to demonstrate how each concept works in practical situations. Provide detailed explanations that uncover different aspects of the material, and don't hesitate to go deep into each idea. "
        f"Also use the additional texbook material to help supplement the narrative you build. Use examples and information from the additional textbooks to help build the narrative which explains the chapter that is the focus, but the supplementary textbooks should not become the focus. "
        f"Instead of summarizing, imagine you are guiding the learner through each concept with patience, ensuring they grasp not just the 'what' but also the 'why' behind the material.\n\n"
        f"Chapter content: {cleaned_chapter_content}\n"
        f"Additional content from other textbooks: {supplementary_content}\n\n"
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
