"""
Local ChromaDB vector store + sentence-transformers embeddings.
Replaces AWS Bedrock Knowledge Base for RAG.
"""
import logging
from functools import lru_cache
from typing import List, Optional

import chromadb
from chromadb import Collection
from sentence_transformers import SentenceTransformer

from core.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _chroma_client() -> chromadb.PersistentClient:
    return chromadb.PersistentClient(path=str(settings.CHROMA_DIR))


@lru_cache(maxsize=1)
def _embedding_model() -> SentenceTransformer:
    logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
    return SentenceTransformer(settings.EMBEDDING_MODEL)


def _embed(texts: List[str]) -> List[List[float]]:
    model = _embedding_model()
    return model.encode(texts, show_progress_bar=False).tolist()


def get_collection(user_id: str, collection_name: str = "documents") -> Collection:
    """Get or create a per-user ChromaDB collection."""
    name = f"{user_id}_{collection_name}"
    return _chroma_client().get_or_create_collection(name=name)


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


def delete_user_collection(user_id: str, collection_name: str = "documents") -> None:
    name = f"{user_id}_{collection_name}"
    try:
        _chroma_client().delete_collection(name=name)
    except Exception:
        pass
