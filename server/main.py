import chardet
import os
import re
import logging 
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, WebSocket, WebSocketDisconnect, Request, APIRouter, Form, Path
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
from pydantic import BaseModel
import textwrap
from functools import lru_cache
import boto3
from fastapi import UploadFile, File, Depends, HTTPException, status, Body
from contextlib import closing
from tempfile import gettempdir
from fastapi.security import OAuth2AuthorizationCodeBearer
from jose import jwt, jwk
from jose.exceptions import JWTError
from jose.utils import base64url_decode
import time
import tempfile
from dotenv import load_dotenv
import ast
import esprima
import json
from botocore.config import Config
import uuid
import requests
from PyPDF2 import PdfReader, PdfWriter
import io
import pikepdf
import mysql.connector
import PyPDF2
import atexit
import fitz  # PyMuPDF
import io
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
import logging
import json
from cachetools import TTLCache

MAX_RETRIES = 1

# Load the .env file
load_dotenv()

S3_BUCKET_NAME = os.getenv('TEXTBOOK_S3_BUCKET')
if not S3_BUCKET_NAME:
    raise ValueError("TEXTBOOK_S3_BUCKET environment variable is not set")

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

# Initialize S3 client
s3_client = boto3.client('s3',
    region_name=os.getenv('AWS_DEFAULT_REGION'),
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
)

# Initialize AWS Textract client
textract_client = boto3.client('textract')  # Add this line

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

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        logging.debug(f"Received token: {token}")
        jwks = get_jwks()
        if not jwks:
            raise HTTPException(status_code=500, detail="Unable to fetch JWKS")
        
        headers = jwt.get_unverified_headers(token)
        logging.debug(f"Token headers: {headers}")
        kid = headers["kid"]
        key_index = next((index for (index, key) in enumerate(jwks) if key["kid"] == kid), None)
        if key_index is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        public_key = jwk.construct(jwks[key_index])
        payload = jwt.decode(
            token,
            public_key.to_pem().decode("utf-8"),
            algorithms=["RS256"],
            audience=os.getenv("COGNITO_APP_CLIENT_ID"),
            options={"verify_exp": True},
        )
        
        # Try different possible keys for user identifier
        user_id = payload.get("username") or payload.get("sub") or payload.get("email")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Unable to identify user from token")
        
        return user_id
    except JWTError as e:
        logging.error(f"JWT Error: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logging.error(f"Unexpected error in get_current_user: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/save-learning-profile")
async def save_learning_profile(
    profile: dict = Body(...),
    current_user: str = Depends(get_current_user)
):
    try:
        S3_BUCKET_NAME = os.getenv('TEXTBOOK_S3_BUCKET')
        profile_key = f"learning_profiles/{current_user}.json"
        
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=profile_key,
            Body=json.dumps(profile),
            ContentType='application/json'
        )
        
        return {"message": "Learning profile saved successfully"}
    except Exception as e:
        logging.error(f"Failed to save learning profile to S3: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to save learning profile")

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

# Add this function to upload files to S3
def upload_file_to_s3(file_name, bucket, object_name=None):
    if object_name is None:
        object_name = file_name
    try:
        s3_client.upload_file(file_name, bucket, object_name)
    except ClientError as e:
        logging.error(e)
        return False
    return True

class PDFUploadResponse(BaseModel):
    message: str
    s3_key: str

@app.post("/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    documentType: str = Form(...),
    tocPages: str = Form(None),
    current_user: str = Depends(get_current_user)
):
    logging.info(f"Received PDF upload request. Document type: {documentType}")
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File format not supported. Please upload a PDF file.")
    
    # Generate a unique filename
    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    s3_key = f"user-uploads/{current_user}/{unique_filename}"
    
    # Save the file temporarily
    temp_file_path = f"/tmp/{unique_filename}"
    with open(temp_file_path, "wb") as buffer:
        buffer.write(await file.read())
    
    try:
        # Upload to S3
        s3_client.upload_file(temp_file_path, S3_BUCKET_NAME, s3_key)
        logging.info(f"File uploaded to S3: {s3_key}")
        
        metadata = {
            "title": file.filename,
            "s3_key": s3_key,
            "user_id": current_user,
            "document_type": documentType,
            "table_of_contents": []  # Initialize with an empty list
        }
        
        if documentType == 'textbook' and tocPages:
            logging.info(f"Processing textbook TOC pages: {tocPages}")
            file_id = unique_filename.split('_')[0]
            start_page, end_page = map(int, tocPages.split('-'))
            toc_structure = process_toc_pages(S3_BUCKET_NAME, s3_key, start_page, end_page, file_id, file.filename, current_user, unique_filename)
            metadata["table_of_contents"] = toc_structure
            logging.info(f"TOC structure extracted: {toc_structure}")
        
        # Save metadata in S3
        metadata_key = f"metadata/{current_user}/{unique_filename}.json"
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=metadata_key,
            Body=json.dumps(metadata),
            ContentType='application/json'
        )
        logging.info(f"Metadata saved to S3: {metadata_key}")
        
        # Clean up the temporary file
        os.remove(temp_file_path)
        return {"message": "PDF uploaded successfully", "s3_key": s3_key}
    except Exception as e:
        logging.error(f"Failed to upload PDF to S3: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to upload PDF")

def process_toc_pages(bucket, document_key, start_page, end_page, file_id, book_title, current_user, unique_filename):
    logging.info(f"Starting Textract processing for document: {document_key}")
    logging.info(f"TOC pages to process: {start_page}-{end_page}")
    
    all_blocks = []
    
    try:
        # Download the PDF from S3
        response = s3_client.get_object(Bucket=bucket, Key=document_key)
        pdf_content = response['Body'].read()

        # Create a temporary file to store the downloaded PDF
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            temp_file.write(pdf_content)
            temp_path = temp_file.name

        # Process each page individually
        for page_num in range(start_page, end_page + 1):
            logging.info(f"Processing page {page_num}")
            
            # Extract and compress the single page
            with pikepdf.Pdf.open(temp_path) as pdf:
                new_pdf = pikepdf.Pdf.new()
                new_pdf.pages.append(pdf.pages[page_num - 1])
                
                # Save the compressed page to a BytesIO object
                output = io.BytesIO()
                new_pdf.save(output, compress_streams=True, object_stream_mode=pikepdf.ObjectStreamMode.generate)
                output.seek(0)
                file_bytes = output.getvalue()

            logging.info(f"Compressed PDF size for page {page_num}: {len(file_bytes)} bytes")
            
            # Process with Textract
            response = textract_client.analyze_document(
                Document={'Bytes': file_bytes},
                FeatureTypes=['TABLES', 'FORMS']
            )
            
            all_blocks.extend(response['Blocks'])

        # Extract chapters and sections with adjusted page numbers
        toc_structure = extract_chapters_from_textract({'Blocks': all_blocks}, end_page + 1)

        logging.info(f"TOC structure extracted: {toc_structure}")
        return toc_structure

    except Exception as e:
        logging.error(f"Error processing TOC pages with Textract: {str(e)}")
        logging.error(f"Error type: {type(e).__name__}")
        logging.error(f"Error args: {e.args}")
        return []

    finally:
        # Clean up the temporary file
        if 'temp_path' in locals():
            os.unlink(temp_path)

def extract_chapters_from_textract(textract_response, content_start_page):
    chapters = []
    current_chapter = None
    current_section = None
    
    for block in textract_response['Blocks']:
        if block['BlockType'] == 'LINE':
            text = block['Text'].strip()
            logging.debug(f"Processing line: {text}")
            
            if text.startswith('Chapter'):
                logging.info(f"Found new chapter: {text}")
                if current_chapter:
                    chapters.append(current_chapter)
                chapter_parts = text.split(':', 1)
                current_chapter = {
                    'number': chapter_parts[0].strip(),
                    'title': chapter_parts[1].strip() if len(chapter_parts) > 1 else '',
                    'sections': []
                }
            elif current_chapter and re.match(r'^\d+\.\d+', text):
                logging.info(f"Found potential section: {text}")
                current_section = {
                    'title': text,
                    'page': None
                }
            elif current_section and text.isdigit():
                # Adjust the page number by adding the content_start_page
                adjusted_page = int(text) + content_start_page - 1
                current_section['page'] = adjusted_page
                logging.debug(f"Created section: {current_section}")
                if current_section['title'] and current_section['page']:
                    current_chapter['sections'].append(current_section)
                    logging.info(f"Added section: {current_section} to chapter {current_chapter['number']}")
                current_section = None
    
    if current_chapter:
        chapters.append(current_chapter)
    
    # Detailed logging of the final structure
    logging.info("Final chapter structure:")
    for chapter in chapters:
        logging.info(f"Chapter {chapter['number']}: {chapter['title']}")
        logging.info(f"  Sections: {chapter['sections']}")
    
    total_sections = sum(len(ch['sections']) for ch in chapters)
    logging.info(f"Extracted {len(chapters)} chapters with a total of {total_sections} sections")
    return chapters

def get_text_from_block(textract_response, block):
    if 'Text' in block:
        return block['Text']
    elif 'Relationships' in block:
        child_blocks = [b for b in textract_response['Blocks'] if b['Id'] in block['Relationships'][0]['Ids']]
        return ' '.join([get_text_from_block(textract_response, child) for child in child_blocks])
    return ''

@app.get("/user-books")
async def get_user_books(current_user: str = Depends(get_current_user)):
    S3_BUCKET_NAME = os.getenv('TEXTBOOK_S3_BUCKET')
    try:
        # List objects in the user's metadata folder
        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET_NAME,
            Prefix=f"metadata/{current_user}/"
        )
        
        books = []
        for obj in response.get('Contents', []):
            metadata = json.loads(s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=obj['Key'])['Body'].read())
            books.append({"title": metadata['title'], "s3_key": metadata['s3_key']})
        
        return books
    except Exception as e:
        logging.error(f"Failed to retrieve user books from S3: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve user books")

@app.get("/download-book/{s3_key}")
async def download_book(s3_key: str, current_user: str = Depends(get_current_user)):
    S3_BUCKET_NAME = os.getenv('TEXTBOOK_S3_BUCKET')
    try:
        # Verify that the book belongs to the current user
        if not s3_key.startswith(f"user-uploads/{current_user}/"):
            raise HTTPException(status_code=403, detail="You don't have permission to access this book")
        
        response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
        return StreamingResponse(
            response['Body'].iter_chunks(),
            media_type='application/pdf',
            headers={"Content-Disposition": f"attachment; filename={s3_key.split('/')[-1]}"}
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            raise HTTPException(status_code=404, detail="Book not found")
        logging.error(f"Failed to download PDF from S3: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to download PDF")

def generate_game_idea(text: str, chapter_id: int, max_attempts=1, max_tokens=4096):
    cleaned_text = text

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
async def generate_narrative_endpoint(chapter_id: int, request: Request):
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

        narrative = generate_narrative(narrative_prompt)
        
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

@app.post("/api/chat")
async def chat(request: Request):
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
async def generate_diagrams_endpoint(request: Request):
    data = await request.json()
    chapter_content = data.get('chapter_content', '')
    generated_summary = data.get('generated_summary', '')
    
    try:
        cleaned_chapter_content = chapter_content
        cleaned_summary = generated_summary
        
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
    
async def generate_diagrams(prompt: str, max_attempts=1, max_tokens=4096):
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

@app.get("/user-textbooks")
async def get_user_textbooks(current_user: str = Depends(get_current_user)):
    try:
        # List objects in the user's metadata folder
        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET_NAME,
            Prefix=f"metadata/{current_user}/"
        )
        
        textbooks = []
        for obj in response.get('Contents', []):
            metadata = json.loads(s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=obj['Key'])['Body'].read())
            if metadata.get('document_type') == 'textbook':
                textbooks.append({
                    "title": metadata['title'],
                    "s3_key": metadata['s3_key'],
                    "upload_date": obj['LastModified'].strftime("%Y-%m-%d %H:%M:%S")
                })
        
        return textbooks
    except Exception as e:
        logging.error(f"Failed to retrieve user textbooks from S3: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve user textbooks")

@app.get("/textbook-structure/{user_id}/{file_id}/{filename}")
async def get_textbook_structure(
    user_id: str = Path(...),
    file_id: str = Path(...),
    filename: str = Path(...),
    current_user: str = Depends(get_current_user)
):
    if user_id != current_user:
        raise HTTPException(status_code=403, detail="You don't have permission to access this file")

    metadata_key = f"metadata/{user_id}/{file_id}_{filename}.json"
    print(f"Constructed metadata key: {metadata_key}")

    try:
        # Fetch the metadata file from S3
        response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=metadata_key)
        metadata = json.loads(response['Body'].read().decode('utf-8'))
        print(f"Metadata content: {json.dumps(metadata, indent=2)}")
        print(f"Successfully fetched metadata for key: {metadata_key}")

        # Download and save the PDF
        temp_path = download_and_save_pdf(user_id, file_id, filename)

        # Extract the table of contents from the metadata
        toc = metadata.get('table_of_contents', [])
        print(f"Extracted table of contents: {toc}")

        # Transform the table of contents into the required structure
        book_structure = {
            "chapters": []
        }

        for chapter in toc:
            chapter_structure = {
                "id": chapter['number'],
                "title": f"{chapter['number']}: {chapter['title']}",
                "sections": []
            }
            for section in chapter.get('sections', []):
                chapter_structure['sections'].append({
                    "id": section['title'].split()[0],
                    "title": section['title']
                })
            book_structure['chapters'].append(chapter_structure)

        print(f"Transformed book structure: {book_structure}")
        return book_structure

    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            print(f"Metadata file not found. Key: {metadata_key}")
            raise HTTPException(status_code=404, detail="Textbook structure not found")
        print(f"Error fetching metadata from S3: {str(e)}")
        raise
    except Exception as e:
        print(f"Unexpected error in get_textbook_structure: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")

@app.get("/list-metadata/{user_id}")
async def list_metadata(user_id: str, current_user: str = Depends(get_current_user)):
    if user_id != current_user:
        raise HTTPException(status_code=403, detail="You don't have permission to access this data")
    
    try:
        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET_NAME,
            Prefix=f"metadata/{user_id}/"
        )
        
        files = [obj['Key'] for obj in response.get('Contents', [])]
        return {"metadata_files": files}
    except Exception as e:
        logging.error(f"Error listing metadata files: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list metadata files")

# Create a cache with a maximum of 100 items and a 1-hour TTL
section_cache = TTLCache(maxsize=100, ttl=3600)

@app.get("/get-section-pdf/{user_id}/{file_id}/{filename}/{section_id}")
async def get_section_pdf(user_id: str, file_id: str, filename: str, section_id: str, current_user: str = Depends(get_current_user)):
    cache_key = f"{user_id}_{file_id}_{filename}_{section_id}"
    
    # Check if the section is in the cache
    if cache_key in section_cache:
        logging.info(f"Returning cached section for {cache_key}")
        return StreamingResponse(io.BytesIO(section_cache[cache_key]), media_type="application/pdf", 
                                 headers={"Content-Disposition": f"attachment; filename={section_id}.pdf"})

    logging.info(f"Fetching section PDF for file_id: {file_id}, filename: {filename}, section_id: {section_id}")
    
    # Fetch metadata (same as before)
    metadata_key = f"metadata/{user_id}/{file_id}_{filename}.json"
    try:
        metadata_obj = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=metadata_key)
        metadata = json.loads(metadata_obj['Body'].read().decode('utf-8'))
    except Exception as e:
        logging.error(f"Error fetching metadata: {str(e)}")
        raise HTTPException(status_code=404, detail="Metadata not found")

    # Find the section in the table of contents (same as before)
    toc = metadata.get('table_of_contents', [])
    section = None
    next_section = None
    for chapter in toc:
        for i, s in enumerate(chapter['sections']):
            if s['title'].startswith(section_id):
                section = s
                if i + 1 < len(chapter['sections']):
                    next_section = chapter['sections'][i + 1]
                break
        if section:
            break

    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    # Determine the end page (same as before)
    if next_section:
        end_page = next_section['page'] - 1
    else:
        chapter_index = toc.index(chapter)
        if chapter_index + 1 < len(toc):
            end_page = toc[chapter_index + 1]['sections'][0]['page'] - 1
        else:
            end_page = section['page'] + 50  # Arbitrary number, adjust as needed

    logging.info(f"Extracting pages {section['page']} to {end_page}")

    # Use the existing temporary file
    temp_key = f"{user_id}_{file_id}_{filename}"
    if temp_key not in temp_pdfs:
        # If the temporary file doesn't exist, download it
        temp_path = download_and_save_pdf(user_id, file_id, filename)
    else:
        temp_path = temp_pdfs[temp_key]

    # Extract the section pages using PyMuPDF
    pdf_document = fitz.open(temp_path)
    output_pdf = fitz.open()

    for page_num in range(section['page'] - 1, min(end_page, len(pdf_document))):
        output_pdf.insert_pdf(pdf_document, from_page=page_num, to_page=page_num)

    # Save the extracted pages to a new PDF
    output_buffer = io.BytesIO()
    output_pdf.save(output_buffer)
    output_buffer.seek(0)

    # Cache the extracted section
    section_cache[cache_key] = output_buffer.getvalue()

    logging.info("Successfully extracted and prepared PDF section")

    return StreamingResponse(output_buffer, media_type="application/pdf", 
                             headers={"Content-Disposition": f"attachment; filename={section_id}.pdf"})

# Global dictionary to store temporary file paths
temp_pdfs = {}

def download_and_save_pdf(user_id, file_id, filename):
    temp_key = f"{user_id}_{file_id}_{filename}"
    if temp_key in temp_pdfs:
        logging.info(f"Using existing temporary PDF: {temp_pdfs[temp_key]}")
        return temp_pdfs[temp_key]

    s3_key = f"user-uploads/{user_id}/{file_id}_{filename}"
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, f"{file_id}_{filename}")
    
    try:
        response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
        with open(temp_path, 'wb') as f:
            f.write(response['Body'].read())
        temp_pdfs[temp_key] = temp_path
        logging.info(f"PDF downloaded and saved temporarily: {temp_path}")
        return temp_path
    except Exception as e:
        logging.error(f"Error downloading PDF: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to download PDF")

# Function to clean up temporary files
def cleanup_temp_files():
    for temp_path in temp_pdfs.values():
        try:
            os.remove(temp_path)
            logging.info(f"Temporary file removed: {temp_path}")
        except Exception as e:
            logging.error(f"Error removing temporary file {temp_path}: {str(e)}")

# Register the cleanup function to run when the server shuts down
atexit.register(cleanup_temp_files)