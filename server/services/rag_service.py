"""
Local RAG service using ChromaDB + sentence-transformers.
Replaces AWS Bedrock Knowledge Base.
"""
import logging
import uuid
from typing import List, Optional

from core.vectorstore import ingest_texts, query, delete_user_collection

logger = logging.getLogger(__name__)


def ingest_section(
    user_id: str,
    file_id: str,
    section_name: str,
    text: str,
    chunk_size: int = 500,
) -> None:
    """Chunk and embed a textbook/transcript section into the user's vector store."""
    if not text.strip():
        return

    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i : i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)

    if not chunks:
        return

    ids = [f"{file_id}_{section_name}_{i}" for i in range(len(chunks))]
    metadatas = [{"file_id": file_id, "section": section_name} for _ in chunks]

    ingest_texts(user_id, chunks, ids, metadatas)
    logger.info(f"Ingested {len(chunks)} chunks for {user_id}/{file_id}/{section_name}")


def retrieve_context(
    user_id: str,
    query_text: str,
    top_k: int = 3,
    file_id: Optional[str] = None,
) -> str:
    """Retrieve and concatenate relevant context for a query."""
    where = {"file_id": file_id} if file_id else None
    docs = query(user_id, query_text, top_k=top_k, where=where)
    if not docs:
        return ""
    return "\n\n".join(docs)


def ingest_transcript(user_id: str, job_id: str, text: str) -> None:
    ingest_section(user_id, "transcriptions", job_id, text)


def ingest_presentation(user_id: str, pres_id: str, text: str) -> None:
    ingest_section(user_id, "presentations", pres_id, text)
