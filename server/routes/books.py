"""
Books API — uploaded PDFs and their sections, the primary unit of study.

    POST   /books                                         upload + ingest (document agent)
    GET    /books                                         list
    GET    /books/{file_id}                               detail with chapters/sections
    DELETE /books/{file_id}
    GET    /books/{file_id}/file                          full PDF
    GET    /books/{file_id}/sections/{section_id}/pdf     section PDF
    GET    /books/{file_id}/sections/{section_id}/study   cached study materials (404 if none)
    POST   /books/{file_id}/sections/{section_id}/study   get-or-generate (content agent)
    POST   /books/{file_id}/sections/{section_id}/study/stream  same, as SSE (token/stage/done/error)
    POST   /books/{file_id}/sections/{section_id}/game    regenerate game (content agent, game graph)
    POST   /books/{file_id}/sections/{section_id}/game/fix  fix the game after a browser error (game graph)
    GET    /books/{file_id}/sections/{section_id}/chat    history
    POST   /books/{file_id}/sections/{section_id}/chat    send message (chat agent)
    POST   /books/{file_id}/sections/{section_id}/chat/stream  same, as an AI SDK UI message stream

Handlers that call the LLM or touch PDFs are sync `def` so FastAPI runs them
in its threadpool instead of blocking the event loop.
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Response, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, StreamingResponse

from agents.chat_agent import get_history, run_chat_agent, stream_chat_agent
from agents.content_agent import (load_cached_materials, run_content_agent, run_game_agent, run_game_fix,
                                  stream_content_agent)
from agents.document_agent import run_document_agent
from core.dependencies import get_user_id
from models.book import BookDetail, BookSummary
from models.study import ChatHistory, ChatRequest, ChatResponse, GameFixRequest, GameResponse, StudyMaterials, StudyRequest
from services import book_service
from utils.streaming_utils import SSE_HEADERS, sse
from utils.ui_stream import UI_STREAM_HEADERS, chat_ui_stream

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/books", tags=["books"])

def _section_or_404(user_id: str, file_id: str, section_id: str) -> None:
    try:
        book_service.get_section(user_id, file_id, section_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


def _section_text(user_id: str, file_id: str, section_id: str) -> str:
    try:
        return book_service.get_section_text(user_id, file_id, section_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Books ─────────────────────────────────────────────────────────────────────

@router.post("", response_model=BookDetail, status_code=201)
def upload_book(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    document_type: str = Form("textbook"),
    toc_pages: Optional[str] = Form(None, description='Printed TOC page range, e.g. "5-9"'),
    user_id: str = Depends(get_user_id),
):
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    result = run_document_agent(file.file.read(), file.filename, user_id, document_type, toc_pages)
    if result["warning"]:
        logger.warning(f"Upload {result['file_id']}: {result['warning']}")
    background.add_task(book_service.index_book, user_id, result["file_id"])
    return book_service.get_book(user_id, result["file_id"])


@router.get("", response_model=List[BookSummary])
def list_books(user_id: str = Depends(get_user_id)):
    return book_service.list_books(user_id)


@router.get("/{file_id}", response_model=BookDetail)
def get_book(file_id: str, user_id: str = Depends(get_user_id)):
    try:
        return book_service.get_book(user_id, file_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Book not found")


@router.delete("/{file_id}", status_code=204)
def delete_book(file_id: str, user_id: str = Depends(get_user_id)):
    try:
        book_service.delete_book(user_id, file_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Book not found")
    return Response(status_code=204)


@router.get("/{file_id}/file")
def get_book_file(file_id: str, user_id: str = Depends(get_user_id)):
    try:
        path = book_service.book_pdf_path(user_id, file_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Book not found")
    return FileResponse(path, media_type="application/pdf", content_disposition_type="inline")


# ── Sections ──────────────────────────────────────────────────────────────────

@router.get("/{file_id}/sections/{section_id}/pdf")
def get_section_pdf(file_id: str, section_id: str, user_id: str = Depends(get_user_id)):
    try:
        data, filename = book_service.get_section_pdf(user_id, file_id, section_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return Response(data, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{filename}"'})


@router.get("/{file_id}/sections/{section_id}/study", response_model=StudyMaterials)
def get_study_materials(file_id: str, section_id: str, user_id: str = Depends(get_user_id)):
    _section_or_404(user_id, file_id, section_id)
    cached = load_cached_materials(user_id, file_id, section_id)
    if not cached:
        raise HTTPException(status_code=404, detail="Study materials not generated yet")
    return cached


@router.post("/{file_id}/sections/{section_id}/study", response_model=StudyMaterials)
def generate_study_materials(
    file_id: str, section_id: str, body: StudyRequest = StudyRequest(), user_id: str = Depends(get_user_id)
):
    text = _section_text(user_id, file_id, section_id)
    try:
        return run_content_agent(text, user_id, scope=file_id, unit_id=section_id,
                                 rag_file_id=file_id, force_regenerate=body.force_regenerate)
    except Exception as e:
        logger.exception("Study material generation failed")
        raise HTTPException(status_code=502, detail=f"Generation failed: {e}")


@router.post("/{file_id}/sections/{section_id}/study/stream")
async def stream_study_materials(
    file_id: str, section_id: str, body: StudyRequest = StudyRequest(), user_id: str = Depends(get_user_id)
):
    text = await run_in_threadpool(_section_text, user_id, file_id, section_id)

    async def events():
        try:
            async for event, data in stream_content_agent(text, user_id, scope=file_id, unit_id=section_id,
                                                          rag_file_id=file_id,
                                                          force_regenerate=body.force_regenerate):
                yield sse(event, data)
        except Exception as e:
            logger.exception("Streaming study generation failed")
            yield sse("error", f"Generation failed: {e}")

    return StreamingResponse(events(), media_type="text/event-stream", headers=SSE_HEADERS)


@router.post("/{file_id}/sections/{section_id}/game", response_model=GameResponse)
def regenerate_game(file_id: str, section_id: str, user_id: str = Depends(get_user_id)):
    text = _section_text(user_id, file_id, section_id)
    try:
        return run_game_agent(text, user_id, scope=file_id, unit_id=section_id, new_idea=True)
    except LookupError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.exception("Game generation failed")
        raise HTTPException(status_code=502, detail=f"Generation failed: {e}")


@router.post("/{file_id}/sections/{section_id}/game/fix", response_model=GameResponse)
def fix_game(file_id: str, section_id: str, body: GameFixRequest, user_id: str = Depends(get_user_id)):
    _section_or_404(user_id, file_id, section_id)
    try:
        return run_game_fix(user_id, scope=file_id, unit_id=section_id, **body.model_dump())
    except LookupError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.exception("Game fix failed")
        raise HTTPException(status_code=502, detail=f"Fix failed: {e}")


@router.get("/{file_id}/sections/{section_id}/chat", response_model=ChatHistory)
def get_chat(file_id: str, section_id: str, user_id: str = Depends(get_user_id)):
    _section_or_404(user_id, file_id, section_id)
    return {"history": get_history(user_id, file_id, section_id)}


@router.post("/{file_id}/sections/{section_id}/chat", response_model=ChatResponse)
def send_chat(file_id: str, section_id: str, body: ChatRequest, user_id: str = Depends(get_user_id)):
    _section_text(user_id, file_id, section_id)  # 404s, and indexes the section for the tutor
    try:
        return run_chat_agent(body.message, [book_service.section_source(user_id, file_id, section_id)], user_id, scope=file_id, unit_id=section_id,
                              rag_file_id=file_id, language=body.language)
    except Exception as e:
        logger.exception("Chat failed")
        raise HTTPException(status_code=502, detail=f"Chat failed: {e}")


@router.post("/{file_id}/sections/{section_id}/chat/stream")
async def stream_chat(file_id: str, section_id: str, body: ChatRequest, user_id: str = Depends(get_user_id)):
    await run_in_threadpool(_section_text, user_id, file_id, section_id)  # as in send_chat
    sources = [book_service.section_source(user_id, file_id, section_id)]
    events = stream_chat_agent(body.message, sources, user_id, scope=file_id, unit_id=section_id,
                               rag_file_id=file_id, language=body.language)
    return StreamingResponse(chat_ui_stream(events, logger), media_type="text/event-stream",
                             headers=UI_STREAM_HEADERS)
