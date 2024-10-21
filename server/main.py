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
from jose import jwt, JWTError
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

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

# Cognito configuration
REGION = os.getenv('AWS_DEFAULT_REGION')
USER_POOL_ID = os.getenv('COGNITO_USER_POOL_ID')
APP_CLIENT_ID = os.getenv('COGNITO_APP_CLIENT_ID')
JWKS_URL = os.getenv('COGNITO_JWKS_URL')

# Fetch the JWKS from Cognito
jwks = requests.get(JWKS_URL).json()['keys']

security = HTTPBearer()

def decode_token(token: str):
    try:
        # Get the kid from the headers prior to verification
        headers = jwt.get_unverified_headers(token)
        kid = headers['kid']
        
        # Search for the kid in the downloaded public keys
        key_index = -1
        for i in range(len(jwks)):
            if kid == jwks[i]['kid']:
                key_index = i
                break
        if key_index == -1:
            raise HTTPException(status_code=401, detail='Public key not found in jwks.json')
        
        # Construct the public key
        public_key = jwk.construct(jwks[key_index])
        
        # Get the last two sections of the token,
        # message and signature (encoded in base64)
        message, encoded_signature = str(token).rsplit('.', 1)
        
        # Decode the signature
        decoded_signature = base64url_decode(encoded_signature.encode('utf-8'))
        
        # Verify the signature
        if not public_key.verify(message.encode("utf8"), decoded_signature):
            raise HTTPException(status_code=401, detail='Signature verification failed')
        
        # Since we passed the verification, we can now safely
        # use the unverified claims
        claims = jwt.get_unverified_claims(token)
        
        # Additionally we can verify the token expiration
        if time.time() > claims['exp']:
            raise HTTPException(status_code=401, detail='Token is expired')
        
        # And the Audience  (use claims['client_id'] if verifying an access token)
        if claims['aud'] != APP_CLIENT_ID:
            raise HTTPException(status_code=401, detail='Token was not issued for this audience')
        
        # Now we can use the claims
        return claims['sub']  # This is the user ID
    except JWTError:
        raise HTTPException(status_code=401, detail='Invalid token')

def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    try:
        token = credentials.credentials
        return decode_token(token)
    except AttributeError:
        raise HTTPException(status_code=401, detail="Invalid authorization credentials")
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

learningCategories = {
    "Visual": [
        "I find it easier to understand new information when it is presented in diagrams, charts, or graphs.",
        "I prefer learning new concepts by observing demonstrations.",
        "I often visualize concepts or problems in my mind to help me solve them.",
        "I use colors, symbols, or drawings when taking notes to help me organize my thoughts.",
        "I remember information better when I see it written down or displayed on a screen",
    ],
    "Auditory": [
        "I learn better when I listen to explanations rather than read them.",
        "I prefer to learn by listening to audio lectures or podcasts.",
        "I remember information better when I hear it spoken aloud.",
        "I use mnemonics or chants to help me memorize information.",
        "I learn best by discussing concepts with others.",
    ],
    "ReadingWriting": [
        "I understand new ideas best when I write them down.",
        "I learn best by reading textbooks or articles.",
        "I use flashcards or mind maps to help me memorize information.",
        "I prefer to learn by reading and writing rather than listening or watching.",
        "I use diagrams or charts to help me understand and remember information.",
    ],
    "Kinesthetic": [
        "I enjoy working with physical models or doing hands-on activities to learn.",
        "I learn best by doing experiments or practical activities.",
        "I use role-playing or simulations to help me understand and apply new concepts.",
        "I prefer to learn by solving real-world problems or puzzles.",
        "I use physical models or manipulatives to help me visualize and understand information.",
    ]
}

@app.post("/save-learning-profile")
async def save_learning_profile(
    profile: dict = Body(...),
    current_user: str = Depends(get_current_user)
):
    try:
        S3_BUCKET_NAME = os.getenv('TEXTBOOK_S3_BUCKET')
        
        # Generate the text-based learning profile description
        learning_profile_description = generate_learning_profile_description(profile['answers'], learningCategories)
        
        # Create a dictionary with both the original answers and the generated description
        full_profile = {
            "answers": profile['answers'],
            "description": learning_profile_description
        }
        
        profile_key = f"learning_profiles/{current_user}.json"
        
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=profile_key,
            Body=json.dumps(full_profile),
            ContentType='application/json'
        )
        
        return {"message": "Learning profile saved successfully", "description": learning_profile_description}
    except Exception as e:
        logging.error(f"Failed to save learning profile to S3: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to save learning profile")

def generate_learning_profile_description(answers: dict, questionnaire: dict) -> str:
    prompt = f"""Based on the following questionnaire answers, generate a paragraph-long textual description of the user's learning style. The answers are organized by learning category (Visual, Auditory, ReadingWriting, Kinesthetic) and represent the user's agreement level with each statement (1: Strongly Disagree, 5: Strongly Agree).

Questionnaire:
{json.dumps(questionnaire, indent=2)}

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

async def query_knowledge_base(query: str, top_k: int = 3):
    try:
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

def generate_game_idea(text: str, learning_profile: str, max_attempts=1, max_tokens=4096):
    prompt = f"""Based on the following chapter content and the user's learning profile, suggest a simple interactive game idea that reinforces the key concepts. The game should:
    1. Be implementable in JavaScript
    2. Reinforce one or more key concepts from the chapter
    3. Be engaging and educational for students
    4. Be described in 2-3 sentences
    5. Be tailored to the user's learning style as described in their profile

    Additionally, provide a brief summary of the chapter's main concepts (2-3 sentences).

    Use clear, engaging language suitable for a student new to these concepts. 
    Use LaTeX formatting for mathematical equations. Enclose LaTeX expressions in dollar signs for inline equations ($...$) and double dollar signs for display equations ($$...$$).

    Chapter content: {text}

    User's learning profile: {learning_profile}

    Now, provide a brief summary of the chapter's key concepts, followed by an engaging game idea tailored to the user's learning style:"""

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

@app.post("/generate-narrative")
async def generate_narrative_endpoint(request: Request, current_user: str = Depends(get_current_user)):
    try:
        data = await request.json()
        chapter_content = data.get('chapter_content', '')
        file_id = data.get('file_id', '')
        section_id = data.get('section_id', '')
        force_regenerate = data.get('force_regenerate', False)

        user_id = current_user  # This is now fetched from the token

        if not user_id:
            logging.error("user_id is empty in generate_narrative_endpoint")
            raise HTTPException(status_code=400, detail="User authentication failed")

        narrative_key = f"narratives/{user_id}/{file_id}/{section_id}.json"
        game_idea_key = f"game_ideas/{user_id}/{file_id}/{section_id}.json"

        if not force_regenerate:
            try:
                existing_narrative = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=narrative_key)
                existing_game_idea = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=game_idea_key)
                narrative_data = json.loads(existing_narrative['Body'].read().decode('utf-8'))
                game_idea_data = json.loads(existing_game_idea['Body'].read().decode('utf-8'))
                return {**narrative_data, **game_idea_data}
            except s3_client.exceptions.NoSuchKey:
                # If either file doesn't exist, proceed with generation
                pass

        # Fetch the user's learning profile
        learning_profile = get_learning_profile(user_id)

        logging.info("Received learning_profile: {learning_profile}")

        # Query the knowledge base
        relevant_info = await query_knowledge_base(chapter_content[:2000])

        # Check if relevant_info is an error message
        if relevant_info.startswith("Error") or relevant_info.startswith("Unexpected error"):
            logging.warning(f"Knowledge base query failed: {relevant_info}")
            relevant_info = "No additional information available."

        # Generate narrative
        narrative_prompt = f"""
        Generate an extensive, in-depth narrative summary for the following chapter content, 
        incorporating the provided relevant information from the knowledge base and tailoring it to the user's learning profile:

        Chapter content: {chapter_content}

        Relevant information from knowledge base: {relevant_info}

        Learning profile: {learning_profile}

        Please create a comprehensive, detailed summary that:

        1. Thoroughly explains all key concepts, formulas, and theorems presented in the chapter, providing step-by-step derivations where applicable.
        2. Elaborates on each subtopic within the chapter, ensuring no important detail is omitted.
        3. Provides multiple examples for each concept, ranging from simple to complex, to illustrate the application of the ideas.
        4. Draws connections between different concepts within the chapter and to broader contexts in the field of study.
        5. Uses rich, vivid analogies and real-world examples to make complex ideas more accessible and relatable.
        6. Integrates the relevant information from the knowledge base to provide additional context, historical background, or advanced applications of the concepts.
        7. Discusses the significance and practical applications of the topic in various fields (e.g., physics, engineering, economics, etc., as appropriate for the subject matter).
        8. Addresses common misconceptions, potential areas of confusion, and frequently asked questions related to the topic.
        9. Includes thought-provoking questions and prompts throughout the narrative to encourage active engagement with the material.
        10. Incorporates elements that cater to the user's learning profile, such as visual aids for visual learners, auditory cues for auditory learners, or hands-on activities for kinesthetic learners.
        11. Provides a detailed explanation of any graphs, charts, or diagrams mentioned in the chapter, describing their features and significance.
        12. Discusses any historical context or the development of the concepts over time, if relevant.
        13. Explains the implications and importance of the concepts for future topics in the subject.
        14. Includes practice problems or exercises with detailed solutions to reinforce understanding.
        15. Summarizes key points at the end of each major section to aid in retention and review.

        The summary should be highly informative, engaging, and comprehensive. Aim for a length that thoroughly covers all aspects of the chapter content, using at least 75% of the available 8192 token limit. Ensure that the explanation is not only extensive but also clear and accessible, breaking down complex ideas into manageable parts.
        """

        narrative = generate_narrative(narrative_prompt)
        
        # Generate game idea
        game_response = generate_game_idea(chapter_content, learning_profile)
        
        # Generate game code
        game_code_response = await generate_game_code(GameIdeaRequest(game_idea=game_response))
        game_code = game_code_response.get("code", "")

        narrative_result = {
            "narrative": narrative
        }

        game_result = {
            "game_idea": game_response,
            "game_code": game_code
        }

        # Save the generated narrative to S3
        s3_client.put_object(Bucket=S3_BUCKET_NAME, Key=narrative_key, Body=json.dumps(narrative_result))
        
        # Save the generated game idea and code to S3
        s3_client.put_object(Bucket=S3_BUCKET_NAME, Key=game_idea_key, Body=json.dumps(game_result))

        return {**narrative_result, **game_result}

    except Exception as e:
        logging.exception("Error in generate_narrative_endpoint")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    try:
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

    except Exception as e:
        logging.exception("Error in transcribe_audio")
        raise HTTPException(status_code=500, detail=str(e))

def get_learning_profile(user_id):
    if not user_id:
        logging.error("get_learning_profile called with empty user_id")
        return "Learning profile not available."

    try:
        profile_key = f"learning_profiles/{user_id}.json"
        response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=profile_key)
        profile_data = json.loads(response['Body'].read().decode('utf-8'))
        return profile_data.get('description', 'Learning profile not available.')
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            logging.error(f"Learning profile not found for user_id: {user_id}")
        else:
            logging.error(f"Error fetching learning profile: {str(e)}")
        return "Learning profile not available."
    except Exception as e:
        logging.error(f"Unexpected error in get_learning_profile: {str(e)}")
        return "Learning profile not available."
    
def generate_narrative(prompt: str, max_attempts=1, max_tokens=8192):
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
        user_id = data.get('userId')
        file_id = data.get('fileId')
        section_name = data.get('sectionName')
        language = data.get('language', 'en')
        force_regenerate = data.get('forceRegenerate')
        logging.info(f"Received chat request for section: {section_name}, force_regenerate: {force_regenerate}")

        if not user_message or not user_id or not file_id or not section_name:
            raise HTTPException(status_code=400, detail="Missing required parameters")

        # Retrieve the extracted text from S3
        extracted_text_key = f"extracted-text/{user_id}/{file_id}/section_{section_name}.txt"
        try:
            extracted_text_obj = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=extracted_text_key)
            extracted_text = extracted_text_obj['Body'].read().decode('utf-8')
        except ClientError as e:
            logging.error(f"Error retrieving extracted text: {e}")
            extracted_text = "No extracted text available."

        # Retrieve the generated summary narrative from S3
        narrative_key = f"narratives/{user_id}/{file_id}/{section_name}_{force_regenerate}.json"
        try:
            narrative_obj = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=narrative_key)
            narrative_data = json.loads(narrative_obj['Body'].read().decode('utf-8'))
            generated_summary = narrative_data.get('narrative', '')
        except ClientError as e:
            logging.error(f"Error retrieving narrative: {e}")
            generated_summary = "No generated summary available."

        # Retrieve chat history from S3
        chat_history_key = f"chat-history/{user_id}/{file_id}/{section_name}.json"
        try:
            chat_history_obj = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=chat_history_key)
            chat_history = json.loads(chat_history_obj['Body'].read().decode('utf-8'))
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                chat_history = []
            else:
                logging.error(f"Error retrieving chat history: {e}")
                chat_history = []

        # Retrieve knowledge base information
        knowledge_base_info = await query_knowledge_base(extracted_text[:2000])

        if knowledge_base_info is None:
            knowledge_base_info = ""
            logging.error("Knowledge base info is None")
            
        # Translate user message to English if not already in English
        if language != 'en':
            user_message = translate_text(user_message, 'en')

        context = f"""You are an AI tutor assisting a student with their studies. 
        The current section content is: {extracted_text}... 
        The generated summary of this section is: {generated_summary}...
        Relevant information from the knowledge base is: {knowledge_base_info[:2000]}...
        Please ensure your responses are relevant to this topic."""

        prompt = f"""Here's the user's learning profile: {get_learning_profile(user_id)}

        {context}

        Remember the context of the previous messages in this conversation. Here's the student's latest question:

        {user_message}

        Provide a helpful, accurate, and concise answer based on the given context, your general knowledge, and the conversation history. Make sure to reference the section content in your answer. Answer the question but be as concise as possible (4-6 sentences)."""

        # Generate AI response using the chat function
        ai_response = generate_chat_response(prompt, chat_history)

        # Translate AI response if not in English
        if language != 'en':
            ai_response = translate_text(ai_response, language)

        # Update chat history
        chat_history.append({"user": "You", "text": data.get('message')})  # Use original message for history
        chat_history.append({"user": "AI", "text": ai_response})

        # Save updated chat history to S3
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=chat_history_key,
            Body=json.dumps(chat_history),
            ContentType='application/json'
        )

        return {"reply": ai_response}

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
async def generate_diagrams_endpoint(request: Request, current_user: str = Depends(get_current_user)):
    try:
        data = await request.json()
        chapter_content = data.get('chapter_content', '')
        generated_summary = data.get('generated_summary', '')
        
        user_id = current_user
        
        # Fetch the user's learning profile
        learning_profile = get_learning_profile(user_id)

        # Construct the prompt
        prompt = f"""
        Based on the following chapter content, generated summary, and the user's learning profile, create a set of diagrams that illustrate the key concepts:

        Chapter content: {chapter_content}

        Generated summary: {generated_summary}

        User's learning profile: {learning_profile}

        Here's a template for the diagrams:
        ```mermaid
        graph TD
            A[First Concept] --> B[Second Concept]
            B --> C[Third Concept]
            C --> D[Fourth Concept]
            D --> E[Fifth Concept]
        ```

        Please create diagrams that:
        1. Illustrate the main concepts and their relationships
        2. Are clear and easy to understand
        3. Are tailored to the user's learning style as described in their profile
        4. Use appropriate visual representations (e.g., flowcharts, mind maps, etc.)

        Some extra guidelines:
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

        Provide the diagrams in Mermaid syntax.
        """

        # Generate diagrams
        diagrams = await generate_diagrams(prompt)

        return {"diagrams": diagrams}

    except HTTPException as he:
        # This will catch the HTTPException raised in generate_diagrams
        raise he
    except Exception as e:
        logging.error(f"Unexpected error in generate_diagrams_endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")
    
async def generate_diagrams(prompt: str):
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
            modelId="anthropic.claude-3-5-sonnet-20240620-v1:0",
            body=request
        )

        full_response = ""
        for event in response['body']:
            chunk = json.loads(event['chunk']['bytes'])
            if chunk['type'] == 'content_block_delta':
                full_response += chunk['delta'].get('text', '')

        # Extract Mermaid diagrams from the response
        diagrams = re.findall(r'```mermaid\n(.*?)\n```', full_response, re.DOTALL)
        
        if diagrams:
            return diagrams
        else:
            logging.warning("No diagrams found in the response.")
            return []

    except ClientError as e:
        error_message = f"Error generating diagrams: {str(e)}"
        logging.error(error_message)
        raise HTTPException(status_code=500, detail=error_message)
    except Exception as e:
        error_message = f"Unexpected error generating diagrams: {str(e)}"
        logging.error(error_message)
        raise HTTPException(status_code=500, detail=error_message)

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

    # Create a sanitized filename from the section title
    sanitized_title = "".join(c for c in section['title'] if c.isalnum() or c in (' ', '-', '_')).rstrip()
    pdf_filename = f"{sanitized_title}.pdf"
    print(f"Sanitized title: {sanitized_title}, PDF filename: {pdf_filename}")

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
                             headers={"Content-Disposition": f"attachment; filename={pdf_filename}"})

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

@app.post("/process-pdf-section")
async def process_pdf_section(
    user_id: str = Form(...),
    file_id: str = Form(...),
    filename: str = Form(...),
    section_name: str = Form(...),
    current_user: str = Depends(get_current_user)
):
    try:
        logging.info(f"Received request for process_pdf_section:")
        logging.info(f"user_id: {user_id}")
        logging.info(f"file_id: {file_id}")
        logging.info(f"filename: {filename}")
        logging.info(f"section_name: {section_name}")
        logging.info(f"current_user: {current_user}")

        if user_id != current_user:
            logging.warning(f"Permission denied: user_id ({user_id}) does not match current_user ({current_user})")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You don't have permission to access this file")

        # Fetch metadata
        metadata_key = f"metadata/{user_id}/{file_id}_{filename}.json"
        try:
            metadata_obj = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=metadata_key)
            metadata = json.loads(metadata_obj['Body'].read().decode('utf-8'))
        except Exception as e:
            logging.error(f"Error fetching metadata: {str(e)}")
            raise HTTPException(status_code=404, detail="Metadata not found")

        # Find the section in the table of contents
        toc = metadata.get('table_of_contents', [])
        section = None
        next_section = None
        for chapter in toc:
            for i, s in enumerate(chapter['sections']):
                if s['title'] == section_name:
                    section = s
                    if i + 1 < len(chapter['sections']):
                        next_section = chapter['sections'][i + 1]
                    break
            if section:
                break

        if not section:
            raise HTTPException(status_code=404, detail="Section not found")

        start_page = section['page']
        if next_section:
            end_page = next_section['page'] - 1
        else:
            chapter_index = toc.index(chapter)
            if chapter_index + 1 < len(toc):
                end_page = toc[chapter_index + 1]['sections'][0]['page'] - 1
            else:
                end_page = start_page + 50  # Arbitrary number, adjust as needed

        logging.info(f"Processing section '{section_name}' from page {start_page} to {end_page}")

        try:
            s3_key = f"user-uploads/{user_id}/{file_id}_{filename}"
            extracted_text_key = f"extracted-text/{user_id}/{file_id}/section_{section_name}.txt"

            # Check if extracted text already exists in S3
            try:
                existing_text = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=extracted_text_key)
                return {"extracted_text": existing_text['Body'].read().decode('utf-8')}
            except s3_client.exceptions.NoSuchKey:
                # If the file doesn't exist, proceed with extraction
                pass

            extracted_text = ""

            # Download the PDF from S3
            response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
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
                
                # Extract text and table data
                page_text = extract_text_and_tables(response)
                extracted_text += f"Page {page_num}:\n{page_text}\n\n"

            # Save the extracted text to S3
            s3_client.put_object(Bucket=S3_BUCKET_NAME, Key=extracted_text_key, Body=extracted_text)

            return {"extracted_text": extracted_text}

        except Exception as e:
            logging.error(f"Error processing PDF section: {str(e)}")
            raise HTTPException(status_code=500, detail="Error processing PDF section")
        finally:
            # Clean up the temporary file
            if 'temp_path' in locals():
                os.unlink(temp_path)

    except ValueError as ve:
        logging.error(f"ValueError in process_pdf_section: {str(ve)}")
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(ve))
    except Exception as e:
        logging.error(f"Unexpected error in process_pdf_section: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred")

def extract_text_and_tables(textract_response):
    extracted_content = ""
    for item in textract_response['Blocks']:
        if item['BlockType'] == 'LINE':
            extracted_content += item['Text'] + "\n"
        elif item['BlockType'] == 'TABLE':
            extracted_content += "Table:\n"
            for cell in item['Relationships'][0]['Ids']:
                cell_block = next(block for block in textract_response['Blocks'] if block['Id'] == cell)
                if 'Text' in cell_block:
                    extracted_content += cell_block['Text'] + "\t"
                extracted_content += "\n"
            extracted_content += "\n"
    return extracted_content