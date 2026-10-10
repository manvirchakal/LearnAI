"""
Local RAG service using ChromaDB + sentence-transformers.
Replaces AWS Bedrock Knowledge Base.
"""
import logging
import uuid
from dataclasses import dataclass
from typing import List, Optional

from core.vectorstore import delete_user_collection, get_collection, get_records, ingest_texts, query, query_records

logger = logging.getLogger(__name__)


def ingest_section(
    user_id: str,
    file_id: str,
    section_name: str,
    text: str,
    chunk_size: int = 300,  # words; ~400 tokens fits 512-token embedding models
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



def source_id(file_id: str, section: str) -> str:
    """How the tutor names one ingested section: "<file_id>/<section>"."""
    return f"{file_id}/{section}"


def parse_source(source: str) -> Optional[tuple]:
    """(file_id, section) of a source id, or None if it isn't one."""
    file_id, _, section = source.partition("/")
    return (file_id, section) if file_id and section else None


@dataclass
class Passage:
    """A retrieved chunk and where it sits in its source (one ingested section)."""
    file_id: str
    section: str
    text: str
    start: int  # character offset in section_text()
    source_length: int


def _chunk_index(chunk_id: str) -> int:
    return int(chunk_id.rsplit("_", 1)[1])  # ids are f"{file_id}_{section}_{i}"


def _section_chunks(user_id: str, file_id: str, section: str) -> List[str]:
    records = get_records(user_id, {"$and": [{"file_id": file_id}, {"section": section}]})
    return [text for chunk_id, text, _ in sorted(records, key=lambda r: _chunk_index(r[0]))]


def section_text(user_id: str, file_id: str, section: str) -> Optional[str]:
    """The ingested text of one section, rebuilt from its chunks, or None if there's none."""
    chunks = _section_chunks(user_id, file_id, section)
    return " ".join(chunks) if chunks else None  # chunks split the section's words


def _scope_filter(file_id: Optional[str], sources: Optional[List[str]]) -> Optional[dict]:
    if file_id:
        return {"file_id": file_id}
    if sources is None:
        return None
    clauses = [{"$and": [{"file_id": f}, {"section": s}]} for f, s in map(parse_source, sources)]
    return clauses[0] if len(clauses) == 1 else {"$or": clauses}


def search_passages(user_id: str, query_text: str, top_k: int = 3, file_id: Optional[str] = None,
                    sources: Optional[List[str]] = None) -> List[Passage]:
    """The chunks most relevant to a query, best first, each placed in its section.
    Searches one file if file_id is given, else only the given source ids, if any."""
    if not file_id and sources == []:
        return []
    where = _scope_filter(file_id, sources)
    passages = []
    for chunk_id, text, meta in query_records(user_id, query_text, top_k=top_k, where=where):
        chunks = _section_chunks(user_id, meta["file_id"], meta["section"])
        index = _chunk_index(chunk_id)
        start = sum(len(c) + 1 for c in chunks[:index])
        passages.append(Passage(meta["file_id"], meta["section"], text, start, len(" ".join(chunks))))
    return passages

def ingest_transcript(user_id: str, job_id: str, text: str) -> None:
    ingest_section(user_id, "transcriptions", job_id, text)


def ingest_presentation(user_id: str, pres_id: str, text: str) -> None:
    ingest_section(user_id, "presentations", pres_id, text)


def delete_file_chunks(user_id: str, file_id: str) -> None:
    """Remove every embedded chunk belonging to one file."""
    try:
        get_collection(user_id).delete(where={"file_id": file_id})
    except Exception as e:
        logger.warning(f"Could not delete chunks for {user_id}/{file_id}: {e}")
