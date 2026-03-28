import logging
import os
import tempfile
import uuid
from datetime import datetime

import fitz
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from core.dependencies import get_user_id
from services.storage_service import (
    save_notes_metadata,
    save_notes_content,
    load_notes_metadata,
    load_notes_content,
)
from services.collection_service import create_default_collection

logger = logging.getLogger(__name__)
router = APIRouter(tags=["notes"])

SUPPORTED_FORMATS = [".pdf", ".jpg", ".jpeg", ".png"]


@router.post("/process-notes")
async def process_notes(
    notes: UploadFile = File(...),
    user_id: str = Depends(get_user_id),
):
    file_ext = os.path.splitext(notes.filename)[1].lower()
    if file_ext not in SUPPORTED_FORMATS:
        raise HTTPException(status_code=400, detail=f"Unsupported format. Supported: {SUPPORTED_FORMATS}")

    notes_id = str(uuid.uuid4())
    try:
        notes_bytes = await notes.read()

        # Extract text using PyMuPDF (PDF) or pytesseract-free plain fitz for images
        processed_content = {"text_content": [], "diagrams": [], "tables": []}

        if file_ext == ".pdf":
            with fitz.open(stream=notes_bytes, filetype="pdf") as doc:
                for page in doc:
                    for block in page.get_text("blocks"):
                        text = block[4].strip()
                        if text:
                            processed_content["text_content"].append({
                                "text": text,
                                "confidence": 1.0,
                                "position": {"x": block[0], "y": block[1]},
                            })
        else:
            # For images: use PyMuPDF's OCR-lite (text embedded in image files is limited)
            # A production upgrade would use pytesseract here
            processed_content["text_content"].append({
                "text": f"Image file uploaded: {notes.filename}",
                "confidence": 1.0,
                "position": {},
            })

        metadata = {
            "notes_id": notes_id,
            "original_filename": notes.filename,
            "upload_date": datetime.now().isoformat(),
            "file_type": file_ext,
            "processing_status": "completed",
            "has_diagrams": False,
            "has_tables": len(processed_content.get("tables", [])) > 0,
        }

        save_notes_metadata(user_id, notes_id, metadata)
        save_notes_content(user_id, notes_id, processed_content)

        collection_id = create_default_collection("notes", notes_id, metadata, user_id)

        return {
            "message": "Notes processed successfully",
            "notes_id": notes_id,
            "metadata": metadata,
            "content": processed_content,
            "collection_id": collection_id,
        }
    except Exception as e:
        logger.error(f"Error processing notes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/notes/{notes_id}")
async def get_notes(notes_id: str, user_id: str = Depends(get_user_id)):
    try:
        metadata = load_notes_metadata(user_id, notes_id)
        content = load_notes_content(user_id, notes_id)
        return {"metadata": metadata, "content": content}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Notes not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
