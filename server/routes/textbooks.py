import io
from fastapi import APIRouter, Depends, File, Form, HTTPException, Path, UploadFile
from fastapi.responses import StreamingResponse

from core.dependencies import get_user_id
from services.textbook_service import (
    upload_pdf,
    get_user_books,
    get_user_textbooks,
    get_textbook_structure,
    get_section_pdf_bytes,
    process_pdf_section,
)
from services.storage_service import load_metadata, list_metadata
from core import storage

router = APIRouter(tags=["textbooks"])


@router.post("/upload-pdf")
async def upload_pdf_endpoint(
    file: UploadFile = File(...),
    documentType: str = Form(...),
    tocPages: str = Form(None),
    user_id: str = Depends(get_user_id),
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    try:
        file_bytes = await file.read()
        return await upload_pdf(file_bytes, file.filename, documentType, user_id, tocPages)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user-books")
async def user_books(user_id: str = Depends(get_user_id)):
    return get_user_books(user_id)


@router.get("/user-textbooks")
async def user_textbooks(user_id: str = Depends(get_user_id)):
    return get_user_textbooks(user_id)


@router.get("/textbook-structure/{user_id_path}/{file_id}/{filename}")
async def textbook_structure(
    user_id_path: str = Path(...),
    file_id: str = Path(...),
    filename: str = Path(...),
    user_id: str = Depends(get_user_id),
):
    try:
        return get_textbook_structure(user_id_path, file_id, filename)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Textbook structure not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list-metadata/{user_id_path}")
async def list_metadata_endpoint(user_id_path: str, user_id: str = Depends(get_user_id)):
    files = storage.list_keys(f"metadata/{user_id_path}/")
    return {"metadata_files": files}


@router.get("/download-book/{local_key:path}")
async def download_book(local_key: str, user_id: str = Depends(get_user_id)):
    try:
        data = storage.load_bytes(local_key)
        filename = local_key.split("/")[-1]
        return StreamingResponse(
            io.BytesIO(data),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Book not found")


@router.get("/get-section-pdf/{user_id_path}/{file_id}/{filename}/{section_id}")
async def get_section_pdf(
    user_id_path: str,
    file_id: str,
    filename: str,
    section_id: str,
    user_id: str = Depends(get_user_id),
):
    try:
        pdf_bytes, pdf_filename = get_section_pdf_bytes(user_id_path, file_id, filename, section_id)
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={pdf_filename}"},
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process-pdf-section")
async def process_section(
    user_id_form: str = Form(..., alias="user_id"),
    file_id: str = Form(...),
    filename: str = Form(...),
    section_name: str = Form(...),
    user_id: str = Depends(get_user_id),
):
    try:
        extracted_text = process_pdf_section(user_id_form, file_id, filename, section_name)
        return {"extracted_text": extracted_text}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
