"""
ChromaDB vector store with pluggable embeddings.

EMBEDDING_PROVIDER:
    openai  POST /embeddings on an OpenAI-compatible server (vLLM on the GPU host)
    local   sentence-transformers in-process (needs the [local-ml] extra)

Collections are namespaced by embedding model, so switching models starts a
fresh index instead of mixing incompatible vectors.
"""
import hashlib
import logging
import threading
from functools import lru_cache
from typing import List, Optional, Tuple

import chromadb
from chromadb import Collection

from core.config import settings

logger = logging.getLogger(__name__)

# Background indexing and request-time RAG embed from different threads. Loading
# the local model twice at once, or encoding concurrently on MPS, segfaults the
# process, so the local model is loaded and used by one thread at a time.
_local_model_lock = threading.Lock()
# The same two threads can also open the store together, and two concurrent
# PersistentClient constructions for one path break each other
_chroma_client_lock = threading.Lock()


def _chroma_client() -> chromadb.PersistentClient:
    with _chroma_client_lock:
        return _open_chroma_client()


@lru_cache(maxsize=1)
def _open_chroma_client() -> chromadb.PersistentClient:
    return chromadb.PersistentClient(path=str(settings.CHROMA_DIR),
                                     settings=chromadb.Settings(anonymized_telemetry=False))


@lru_cache(maxsize=1)
def _local_model():
    from sentence_transformers import SentenceTransformer

    logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
    return SentenceTransformer(settings.EMBEDDING_MODEL)


@lru_cache(maxsize=1)
def _openai_client():
    from openai import OpenAI

    return OpenAI(base_url=settings.embedding_base_url, api_key=settings.OPENAI_API_KEY, timeout=120)


def _embed(texts: List[str]) -> List[List[float]]:
    if settings.EMBEDDING_PROVIDER == "local":
        with _local_model_lock:
            return _local_model().encode(texts, show_progress_bar=False).tolist()
    out: List[List[float]] = []
    step = settings.EMBEDDING_BATCH_SIZE
    for i in range(0, len(texts), step):
        resp = _openai_client().embeddings.create(model=settings.EMBEDDING_MODEL, input=texts[i:i + step])
        out.extend(d.embedding for d in sorted(resp.data, key=lambda d: d.index))
    return out


def _collection_name(user_id: str, collection_name: str) -> str:
    # Chroma names are limited to 63 chars of [A-Za-z0-9._-]; hash the parts in
    key = f"{settings.EMBEDDING_PROVIDER}|{settings.EMBEDDING_MODEL}|{user_id}|{collection_name}"
    return f"lai-{hashlib.sha256(key.encode()).hexdigest()[:40]}"


def get_collection(user_id: str, collection_name: str = "documents") -> Collection:
    """Get or create a per-user ChromaDB collection."""
    return _chroma_client().get_or_create_collection(
        name=_collection_name(user_id, collection_name),
        metadata={"user_id": user_id, "collection": collection_name, "embedding_model": settings.EMBEDDING_MODEL},
    )


def ingest_texts(
    user_id: str,
    texts: List[str],
    ids: List[str],
    metadatas: Optional[List[dict]] = None,
    collection_name: str = "documents",
) -> None:
    """Embed and store texts in the user's ChromaDB collection."""
    if not texts:
        return
    col = get_collection(user_id, collection_name)
    embeddings = _embed(texts)
    col.upsert(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas or [{} for _ in texts],
    )
    logger.info(f"Ingested {len(texts)} documents for user {user_id}")


def query(
    user_id: str,
    query_text: str,
    top_k: int = 3,
    collection_name: str = "documents",
    where: Optional[dict] = None,
) -> List[str]:
    """Retrieve top-k relevant text chunks for a query."""
    col = get_collection(user_id, collection_name)
    count = col.count()
    if count == 0:
        return []

    query_embedding = _embed([query_text])[0]
    kwargs = dict(
        query_embeddings=[query_embedding],
        n_results=min(top_k, count),
        include=["documents"],
    )
    if where:
        kwargs["where"] = where

    results = col.query(**kwargs)
    docs = results.get("documents", [[]])[0]
    return docs



def query_records(
    user_id: str,
    query_text: str,
    top_k: int = 3,
    collection_name: str = "documents",
    where: Optional[dict] = None,
) -> List[Tuple[str, str, dict]]:
    """Top-k (id, text, metadata) for a query, best first."""
    col = get_collection(user_id, collection_name)
    count = col.count()
    if count == 0:
        return []
    kwargs = dict(query_embeddings=[_embed([query_text])[0]], n_results=min(top_k, count),
                  include=["documents", "metadatas"])
    if where:
        kwargs["where"] = where
    results = col.query(**kwargs)
    return list(zip(results["ids"][0], results["documents"][0], results["metadatas"][0]))


def get_records(user_id: str, where: dict, collection_name: str = "documents") -> List[Tuple[str, str, dict]]:
    """Every (id, text, metadata) matching a metadata filter, in no particular order."""
    results = get_collection(user_id, collection_name).get(where=where, include=["documents", "metadatas"])
    return list(zip(results["ids"], results["documents"], results["metadatas"]))

def delete_user_collection(user_id: str, collection_name: str = "documents") -> None:
    try:
        _chroma_client().delete_collection(name=_collection_name(user_id, collection_name))
    except Exception:
        pass
