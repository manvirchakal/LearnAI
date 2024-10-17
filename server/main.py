import chardet
import os
import re
import logging 
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, WebSocket, WebSocketDisconnect, Request, APIRouter
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
from botocore.exceptions import ClientError, BotoCoreError
from server import models
from pydantic import BaseModel
import textwrap
from functools import lru_cache
from sqlalchemy.exc import IntegrityError
import boto3
from fastapi import UploadFile, File, Depends, HTTPException, status, Body
from contextlib import closing
from tempfile import gettempdir
from fastapi.security import OAuth2AuthorizationCodeBearer
from jose import jwt
from jose.exceptions import JWTError
from jose.utils import base64url_decode
import time
import tempfile
from dotenv import load_dotenv
import ast
import esprima
import json
from botocore.config import Config

MAX_RETRIES = 1

# Load the .env file
load_dotenv()

router = APIRouter()

# Add AWS Bedrock client initialization
bedrock = boto3.client(
    service_name='bedrock-runtime',
    region_name=os.getenv('AWS_DEFAULT_REGION'),
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
)

bedrock_agent = boto3.client(
    service_name='bedrock-agent-runtime',
    region_name=os.getenv('AWS_DEFAULT_REGION'),
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    config=Config(region_name=os.getenv('AWS_DEFAULT_REGION'))
)

# Add AWS Translate client initialization
translate = boto3.client('translate')

# Add this with your other AWS client initializations
transcribe = boto3.client('transcribe',
    region_name='us-east-1'
)

# Initialize Polly client
polly_client = boto3.client('polly', region_name='us-east-1')

# Create all tables in the database
Base.metadata.create_all(bind=engine)

# Initialize logging
logging.basicConfig(level=logging.DEBUG)

logging.getLogger('botocore').setLevel(logging.INFO)
logging.getLogger('botocore.parsers').setLevel(logging.WARNING)

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

app.include_router(router)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Configure the OAuth2 scheme
oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=os.getenv("COGNITO_AUTHORIZATION_URL"),
    tokenUrl=os.getenv("COGNITO_TOKEN_URL")
)

# Add this function to fetch and cache the JWKS
@lru_cache()
def get_jwks():
    jwks_url = os.getenv("COGNITO_JWKS_URL")
    response = requests.get(jwks_url)
    return response.json()["keys"]

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        # Get the kid from the headers prior to verification
        headers = jwt.get_unverified_headers(token)
        kid = headers["kid"]
        
        # Search for the kid in the downloaded public keys
        key_index = -1
        for i in range(len(get_jwks())):
            if kid == get_jwks()[i]["kid"]:
                key_index = i
                break
        if key_index == -1:
            raise HTTPException(status_code=401, detail="Public key not found in jwks.json")
        
        # Construct the public key
        public_key = jwk.construct(get_jwks()[key_index])
        
        # Get the last two sections of the token,
        # message and signature (encoded in base64)
        message, encoded_signature = str(token).rsplit(".", 1)
        
        # Decode the signature
        decoded_signature = base64url_decode(encoded_signature.encode("utf-8"))
        
        # Verify the signature
        if not public_key.verify(message.encode("utf8"), decoded_signature):
            raise HTTPException(status_code=401, detail="Signature verification failed")
        
        # Since we passed the verification, we can now safely
        # use the unverified claims
        claims = jwt.get_unverified_claims(token)
        
        # Additionally we can verify the token expiration
        if time.time() > claims["exp"]:
            raise HTTPException(status_code=401, detail="Token is expired")
        
        # And the Audience  (use claims["client_id"] if verifying an access token)
        if claims["aud"] != os.getenv("COGNITO_APP_CLIENT_ID"):
            raise HTTPException(status_code=401, detail="Token was not issued for this audience")
        
        return claims["sub"]
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

@app.post("/save-learning-profile")
async def save_learning_profile(
    profile: dict = Body(...),
    current_user: str = Depends(get_current_user)
):
    try:
        print(f"Received answers: {profile}")  # Log the received answers
        
        # Generate textual description using Claude Haiku
        learning_profile = generate_learning_profile_description(profile['answers'])
        
        with SessionLocal() as db:
            user_profile = db.query(models.UserProfile).filter(models.UserProfile.user_id == current_user).first()
            
            if user_profile:
                user_profile.learning_profile = learning_profile
            else:
                user_profile = models.UserProfile(user_id=current_user, learning_profile=learning_profile)
                db.add(user_profile)
            
            db.commit()
        
        print(f"Saved profile for user {current_user}")  # Log the successful save
        return {"message": "Learning profile saved successfully"}
    except Exception as e:
        print(f"Error saving profile: {str(e)}")  # Log any errors
        raise HTTPException(status_code=500, detail=str(e))

async def query_knowledge_base(query: str, top_k: int = 3):
    try:
        logging.info(f"Querying knowledge base with: {query}")
        response = bedrock_agent.retrieve_and_generate(
            input={'text': query},
            retrieveAndGenerateConfiguration={
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': os.getenv('KNOWLEDGE_BASE_ID'),
                    'modelArn': os.getenv('MODEL_ARN')
                },
                'type': 'KNOWLEDGE_BASE'
            }
        )
        
        logging.info(f"Knowledge base response: {response}")
        
        generated_answer = response.get('output', {}).get('text', '')
        return generated_answer

    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logging.error(f"AWS ClientError in query_knowledge_base: {error_code} - {error_message}")
        logging.error(f"Full error response: {e.response}")
        return f"Error querying knowledge base: {error_code} - {error_message}"
    except Exception as e:
        logging.error(f"Unexpected error in query_knowledge_base: {str(e)}")
        return f"Unexpected error querying knowledge base: {str(e)}"

def generate_learning_profile_description(answers: dict) -> str:
    prompt = f"""Based on the following questionnaire answers, generate a paragraph-long textual description of the user's learning style. The answers are organized by learning category (Visual, Auditory, ReadingWriting, Kinesthetic) and represent the user's agreement level with each statement (1: Strongly Disagree, 5: Strongly Agree).

Questionnaire answers:
{json.dumps(answers, indent=2)}

Please provide a comprehensive description of the user's learning style, highlighting their strengths and preferences across different learning modalities. The description should be informative and tailored to the individual based on their responses."""

    try:
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 300,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ],
            "temperature": 0.7,
            "top_p": 0.9,
        })

        response = bedrock.invoke_model_with_response_stream(
            modelId="anthropic.claude-3-haiku-20240307-v1:0",
            body=body
        )

        full_response = ""
        for event in response['body']:
            chunk = json.loads(event['chunk']['bytes'])
            if chunk['type'] == 'content_block_delta':
                full_response += chunk['delta'].get('text', '')

        return full_response.strip()
    except Exception as e:
        logging.error(f"Error generating learning profile description: {str(e)}")
        return "Error generating learning profile description"
    

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

def generate_narrative(prompt: str, db: Session, max_attempts=1, max_tokens=8192):
    full_response = ""
    for i in range(max_attempts):
        try:
            native_request = {
                'anthropic_version': 'bedrock-2023-05-31',
                'max_tokens': max_tokens,
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

            if full_response.endswith(".") and len(full_response) < max_tokens * 0.9:
                break

        except ClientError as e:
            logging.error(f"Error calling Bedrock: {e}")
            return f"Error: {str(e)}"

    return full_response.strip()

def generate_game_idea(text: str, chapter_id: int, db: Session, max_attempts=1, max_tokens=4096):
    cleaned_text = remove_latex_commands(text)

    prompt = f"""Based on the following chapter content, suggest a simple interactive game idea that reinforces the key concepts. The game should:
    1. Be implementable in JavaScript
    2. Reinforce one or more key concepts from the chapter
    3. Be engaging and educational for students
    4. Be described in 2-3 sentences

    Additionally, provide a brief summary of the chapter's main concepts (2-3 sentences).

    Use clear, engaging language suitable for a student new to these concepts. 
    Use LaTeX formatting for mathematical equations. Enclose LaTeX expressions in dollar signs for inline equations ($...$) and double dollar signs for display equations ($$...$$).

    Chapter content: {cleaned_text}

    Now, provide a brief summary of the chapter's key concepts, followed by an engaging game idea:"""

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

    # Delete existing narrative if it exists
    db.query(models.Narrative).filter(models.Narrative.chapter_id == chapter_id).delete()

    # Create new narrative
    narrative_model = models.Narrative(chapter_id=chapter_id, content=full_response)
    db.add(narrative_model)
    db.commit()    

    return full_response

def translate_text(text, target_language):
    try:
        response = translate.translate_text(
            Text=text,
            SourceLanguageCode='en',
            TargetLanguageCode=target_language
        )
        return response['TranslatedText']
    except ClientError as e:
        logging.error(f"Error translating text: {e}")
        return None

@app.post("/generate-narrative/{chapter_id}")
async def generate_narrative_endpoint(chapter_id: int, request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()
        chapter_content = data.get('chapter_content', '')

        # Query the knowledge base
        relevant_info = await query_knowledge_base(chapter_content[:1000])  # Use first 1000 chars as query
        
        # Check if relevant_info is an error message
        if relevant_info.startswith("Error") or relevant_info.startswith("Unexpected error"):
            logging.warning(f"Knowledge base query failed: {relevant_info}")
            relevant_info = "No additional information available."

        # Prepare the prompt for narrative generation
        narrative_prompt = f"""
        Generate a comprehensive and engaging narrative summary for the following chapter content, 
        incorporating the provided relevant information from the knowledge base:

        Chapter content: {chapter_content}

        Relevant information: {relevant_info}

        Relevant information from knowledge base: {relevant_info}

        Please create an extensive summary that:
        1. Explains all key concepts in a clear and engaging manner.
        2. Highlights important connections and insights within the chapter and to broader contexts.
        3. Uses analogies or examples to illustrate complex ideas.
        4. Integrates the relevant information from the knowledge base to enrich the explanation.
        5. Provides a holistic view of the topic, including its significance and applications.
        6. Addresses potential questions or misconceptions a learner might have.

        The summary should be informative, engaging, and easy to understand. Aim for a length of at least 3 quarters of the chapter content, 
        ensuring thorough coverage of all important aspects of the chapter content and related knowledge.
        """

        narrative = generate_narrative(narrative_prompt, db)
        
        # Generate game idea and code
        game_prompt = f"Based on the following chapter content, create an educational game idea:\n\n{chapter_content}"
        game_response = generate_game_idea(game_prompt, chapter_id, db)
        
        # Generate game code
        game_code_response = await generate_game_code(GameIdeaRequest(game_idea=game_response))
        game_code = game_code_response.get("code", "")

        return {
            "narrative": narrative,
            "game_idea": game_response,
            "game_code": game_code
        }

    except Exception as e:
        logging.exception("Error in generate_narrative_endpoint")
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

class GameIdeaRequest(BaseModel):
    game_idea: str

@app.post("/generate-game-code")
async def generate_game_code(request: GameIdeaRequest):
    game_idea = request.game_idea
    
    prompt = f"""Create a fully functional React component for the following game idea:

    {game_idea}

    The component will be rendered within a DynamicGameComponent. Your task is to generate the code that will be passed to this component.

            ```javascript
            const DynamicGameComponent = (((this is where the game code will be passed in as an argument))) => {{
              const [error, setError] = useState(null);
              const [GameComponent, setGameComponent] = useState(null);

              useEffect(() => {{
                setError(null);
                if (gameCode.startsWith("Error generating game code:")) {{
                  setError(gameCode);
                  return;
                }}
                try {{
                  // Your generated code will be inserted here
                  const ComponentFunction = new Function('React', 'useState', 'useEffect', 'MathJax', `
                    return function Game() {{
                      // Your generated code goes here
                    }}
                  `);

                  const CreatedComponent = () => {{
                    return (
                      <ErrorBoundary>
                        {{ComponentFunction(React, React.useState, React.useEffect, MathJax)}}
                      </ErrorBoundary>
                    );
                  }};
                  setGameComponent(() => CreatedComponent);
                }} catch (err) {{
                  console.error('Error creating game component:', err);
                  setError('Error: (((this is where error output would go))));
                }}
              }}, [gameCode]);

              // ... rest of the component
            }};
            ```

            Requirements:
                1. Use React hooks (useState, useEffect, useRef, useCallback) without React. prefix
                2. Use React.createElement for all element creation (no JSX)
                3. Return a single root element (usually a div) containing all other elements 
                5. Ensure all variables and functions are properly declared
                6. Do not use any external libraries or components not provided
                7. Provide ONLY the JavaScript code, without any explanations or markdown formatting
                8. Do not include 'return function Game() {{' at the beginning or '}}' at the end
                9. Use proper JavaScript syntax (no semicolons after blocks or object literals in arrays)
                10. Do not use 'function' as a variable name, as it is a reserved keyword in JavaScript. Use 'func' or 'mathFunction' instead
                11. Create instructions for the user on how to play the game in the game component and how it relates to the chapter content
                12. When evaluating mathematical expressions or functions, use a safe evaluation method instead of 'eval'. For example:
                    - For simple arithmetic, use basic JavaScript operations
                    - For more complex functions, define them explicitly (e.g., Math.sin, Math.cos, etc.)
                13. Ensure all variables used in calculations are properly defined and initialized
                14. Use try-catch blocks when performing calculations to handle potential errors gracefully
                15. For keyboard input:
                    - Use the useEffect hook to add and remove event listeners for keyboard events
                    - In the event listener, call e.preventDefault() to prevent default browser behavior (like scrolling)
                    - Focus on a game element (like the canvas) when the component mounts to ensure it captures keyboard events
                16. Add a button to start/restart the game, and only capture keyboard input when the game is active
                17. Ensure that the current equation is always visible and properly rendered using plain text or another method
                18. To prevent scrolling when using arrow keys:
                    - Add 'tabIndex={0}' to the game container div to make it focusable
                    - In the useEffect for keyboard events, check if the game container has focus before handling key presses
                19. Display the current function prominently using plain text, and update it whenever it changes
                20. Use requestAnimationFrame for the game loop to ensure smooth animation
                                                                
            Generate the game code now, remember to not include any explanations or comments, just the code:
            """

    try:
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 3000,
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": prompt}]
                }
            ],
            "temperature": 0.7,
            "top_p": 0.9,
        })

        response = bedrock.invoke_model_with_response_stream(
            modelId="anthropic.claude-3-5-sonnet-20240620-v1:0",
            body=body
        )

        generated_code = ""
        for event in response['body']:
            chunk = json.loads(event['chunk']['bytes'])
            if chunk['type'] == 'content_block_delta':
                generated_code += chunk['delta'].get('text', '')

        # Log the generated code for debugging
        logging.debug(f"Generated game code:\n{generated_code}")

        return {"code": generated_code.strip()}

    except Exception as e:
        logging.error(f"Error generating game code: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating game code: {str(e)}")

def validate_js_syntax(code):
    try:
        esprima.parseScript(code)
        return True
    except esprima.Error as e:
        logging.error(f"Syntax error in generated code: {e}")
        return False

def post_process_game_code(code):
    # Remove any potential wrapper function or extra brackets
    code = re.sub(r'^return\s*function\s*\w*\s*\(\)\s*{', '', code)
    code = re.sub(r'}\s*$', '', code)
    
    # Remove semicolons after object literals in array definitions
    code = re.sub(r'({[^}]+});(?=\s*[}\]])', r'\1', code)
    
    # Fix arrow function syntax
    code = re.sub(r'(\w+)\s*=>\s*{', r'\1 => {', code)
    
    # Remove semicolons after function/if/else blocks
    code = re.sub(r'(}\s*);(\s*else|\s*[)\]])', r'\1\2', code)
    
    # Ensure all state variables are properly declared
    state_vars = re.findall(r'const \[(\w+), set\w+\] = useState\((.*?)\);', code)
    for var, initial_value in state_vars:
        if initial_value.strip() == '':
            code = code.replace(f'const [{var}, set{var.capitalize()}] = useState();', 
                                f'const [{var}, set{var.capitalize()}] = useState(null);')
    
    # Fix MathJax.Node syntax if necessary
    code = code.replace('React.createElement(MathJax.Node,', 'React.createElement(MathJax,')
    
    # Remove semicolons inside object literals
    code = re.sub(r'({[^}]+};\s*}', r'\1 }', code)
    
    return code.strip()

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
        chapter_content = data.get('chapter_content', '')
        language = data.get('language', 'en')

        if not user_message or not chapter_content:
            raise HTTPException(status_code=400, detail="Message and chapter content are required")

        # Translate user message to English if not already in English
        if language != 'en':
            user_message = translate_text(user_message, 'en')

        context = f"You are an AI tutor assisting a student with their studies. The current chapter is about: {chapter_content[:200]}... Please ensure your responses are relevant to this topic."

        prompt = f"""{context}

        Remember the context of the previous messages in this conversation. Here's the student's latest question:

        {user_message}

        Provide a helpful, accurate, and concise answer based on the given context, your general knowledge, and the conversation history. Make sure to reference the chapter content in your answer. Answer the question but be as concise as possible (4-6 sentences)."""

        # Generate AI response using the chat function
        ai_response = generate_chat_response(prompt, chat_history)

        # Translate AI response if not in English
        if language != 'en':
            ai_response = translate_text(ai_response, language)

        # Update chat history
        chat_history.append({"user": "You", "text": data.get('message')})  # Use original message for history
        chat_history.append({"user": "AI", "text": ai_response})

        return {"reply": ai_response, "updated_chat_history": chat_history}

    except Exception as e:
        logging.exception("Error in chat endpoint")
        raise HTTPException(status_code=500, detail=str(e))    
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

@app.post("/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    # Save the uploaded file temporarily
    temp_file_path = f"/tmp/{uuid.uuid4()}.wav"
    with open(temp_file_path, "wb") as buffer:
        buffer.write(await audio.read())
    
    job_name = f"transcribe_job_{int(time.time())}"
    job_uri = f"s3://YOUR_S3_BUCKET/{audio.filename}"
    
    # Upload the file to S3 (you need to implement this)
    # upload_to_s3(temp_file_path, "YOUR_S3_BUCKET", audio.filename)
    
    transcribe.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={'MediaFileUri': job_uri},
        MediaFormat='wav',
        LanguageCode='en-US'
    )
    
    while True:
        status = transcribe.get_transcription_job(TranscriptionJobName=job_name)
        if status['TranscriptionJob']['TranscriptionJobStatus'] in ['COMPLETED', 'FAILED']:
            break
        time.sleep(5)
    
    if status['TranscriptionJob']['TranscriptionJobStatus'] == 'COMPLETED':
        result = transcribe.get_transcription_job(TranscriptionJobName=job_name)
        transcript_uri = result['TranscriptionJob']['Transcript']['TranscriptFileUri']
        # Fetch and parse the transcript JSON from the URI
        # You'll need to implement this part
        transcript_text = fetch_and_parse_transcript(transcript_uri)
        return {"transcript": transcript_text}
    else:
        return {"error": "Transcription failed"}

@app.post("/api/synthesize-speech")
async def synthesize_speech(request: Request):
    data = await request.json()
    text = data.get('text')
    language = data.get('language', 'en-US')

    try:
        # Map language codes to Polly voice IDs
        voice_map = {
            'en-US': 'Joanna',
            'es-ES': 'Conchita',
            'fr-FR': 'Celine',
            'de-DE': 'Marlene',
            # Add more languages and voices as needed
        }

        response = polly_client.synthesize_speech(
            Text=text,
            OutputFormat='mp3',
            VoiceId=voice_map.get(language, 'Joanna')
        )

        if "AudioStream" in response:
            with closing(response["AudioStream"]) as stream:
                output = os.path.join(gettempdir(), "speech.mp3")
                try:
                    with open(output, "wb") as file:
                        file.write(stream.read())
                except IOError as error:
                    print(error)
                    raise HTTPException(status_code=500, detail="Error writing audio stream to file")

            return FileResponse(output, media_type='audio/mpeg', filename="speech.mp3")
        else:
            raise HTTPException(status_code=500, detail="Could not stream audio")

    except (BotoCoreError, ClientError) as error:
        print(error)
        raise HTTPException(status_code=500, detail=str(error))

@app.post("/translate")
async def translate_text_endpoint(request: Request):
    data = await request.json()
    text = data.get('text')
    target_language = data.get('target_language')

    if not text or not target_language:
        raise HTTPException(status_code=400, detail="Text and target language are required")

    translated_text = translate_text(text, target_language)

    if translated_text is None:
        raise HTTPException(status_code=500, detail="Translation failed")

    return {"translated_text": translated_text}

@app.post("/generate-diagrams")
async def generate_diagrams_endpoint(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    chapter_content = data.get('chapter_content', '')
    generated_summary = data.get('generated_summary', '')
    
    try:
        cleaned_chapter_content = remove_latex_commands(chapter_content)
        cleaned_summary = remove_latex_commands(generated_summary)
        
        prompt = f"""Based on the following chapter content and generated summary, create Mermaid.js diagram descriptions that illustrate the key concepts visually. For each main concept:

        1. Design a simple flowchart diagram that clearly represents the concept
        2. Use only 'graph TD' (top-down) orientation
        3. Keep the diagrams simple, with no more than 5-7 nodes
        4. Provide a brief explanation of what the diagram represents

        Use the following format for diagram descriptions:

        ```mermaid
        graph TD
            A[First Concept] --> B[Second Concept]
            B --> C[Third Concept]
            C --> D[Fourth Concept]
            D --> E[Fifth Concept]
        ```

        Critical guidelines for creating Mermaid diagrams:
        - Always start with 'graph TD' on its own line
        - Use single letters for node IDs (A, B, C, etc.)
        - Use square brackets for node labels: [Label text]
        - Use only --> for arrows (no labels or other arrow types)
        - Each node and connection should be on its own line
        - Indent each line after 'graph TD' with 4 spaces
        - Use only plain English words in labels, NO mathematical symbols or notation
        - Avoid special characters, apostrophes, or quotation marks in labels
        - Use simple, descriptive text for labels
        - If referring to mathematical concepts, use words instead of symbols (e.g., "First Derivative" instead of "f'(x)")
        - Ensure all nodes are connected in a logical flow

        Chapter content: {cleaned_chapter_content}

        Generated summary: {cleaned_summary}

        Now, provide 2-3 Mermaid.js diagram descriptions for the key concepts, focusing on the most important ideas from both the chapter content and the generated summary. Ensure each diagram follows the guidelines strictly, using only plain English words without any mathematical notation or special characters:"""

        diagrams = await generate_diagrams(prompt, db)
        
        return {"diagrams": diagrams}
    except Exception as e:
        logging.exception("Error in generate_diagrams_endpoint")
        raise HTTPException(status_code=500, detail=str(e))
    
async def generate_diagrams(prompt: str, db: Session, max_attempts=1, max_tokens=4096):
    full_response = ""
    for i in range(max_attempts):
        try:
            native_request = {
                'anthropic_version': 'bedrock-2023-05-31',
                'max_tokens': max_tokens,
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
                modelId="anthropic.claude-3-5-sonnet-20240620-v1:0",
                body=request
            )

            for event in response['body']:
                chunk = json.loads(event['chunk']['bytes'])
                if chunk['type'] == 'content_block_delta':
                    full_response += chunk['delta'].get('text', '')

            if full_response.endswith(".") and len(full_response) < max_tokens * 0.9:
                break

        except ClientError as e:
            logging.error(f"Error calling Bedrock: {e}")
            return f"Error: {str(e)}"

    # Extract Mermaid diagrams from the response
    diagrams = re.findall(r'```mermaid\n(.*?)```', full_response, re.DOTALL)
    
    return diagrams