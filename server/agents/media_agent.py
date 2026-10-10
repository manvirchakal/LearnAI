"""
LangGraph media ingestion agent — lecture audio and YouTube videos to transcripts.

    acquire_audio ▶ transcribe ▶ store ▶ embed ▶ END

Transcripts are stored, embedded for RAG, and filed in a single-item
collection so they can be studied like any other material.

Nodes report progress on LangGraph's custom stream as {"stage", "progress",
"title"?} (stages: downloading, transcribing, saving, indexing); pass
on_progress to receive it.
"""
import logging
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from langgraph.config import get_stream_writer
from langgraph.graph import END, StateGraph

from agents.base import MediaState
from services.collection_service import create_default_collection
from services.media_service import SUPPORTED_MEDIA_FORMATS, download_youtube_audio, transcribe_file
from services.rag_service import ingest_transcript
from services.storage_service import save_transcription_content, save_transcription_metadata

logger = logging.getLogger(__name__)


def _report(stage: str, progress: Optional[float] = None, **fields) -> None:
    get_stream_writer()({"stage": stage, "progress": progress, **fields})


def node_acquire_audio(state: MediaState) -> dict:
    if state["source_type"] == "youtube":
        _report("downloading")
        path, title, video_id = download_youtube_audio(
            state["source_url"], state["work_dir"],
            on_progress=lambda fraction, title: _report("downloading", fraction, title=title))
        return {"audio_path": str(path), "title": state["title"] or title, "video_id": video_id}

    path = Path(state["work_dir"]) / f"upload{Path(state['filename'] or '').suffix.lower()}"
    path.write_bytes(state["source_bytes"])
    return {"audio_path": str(path)}


def node_transcribe(state: MediaState) -> dict:
    _report("transcribing")
    transcript = transcribe_file(state["audio_path"], on_progress=lambda fraction: _report("transcribing", fraction))
    if not transcript.strip():
        raise ValueError("No speech was detected in the audio")
    return {"transcript": transcript}


def node_store(state: MediaState) -> dict:
    _report("saving")
    job_id = uuid.uuid4().hex
    metadata = {
        "job_id": job_id,
        "title": state["title"],
        "original_filename": state["filename"] or state["title"],
        "transcription_date": datetime.now().isoformat(),
        "source_type": state["source_type"],
        "video_url": state["source_url"],
        "video_id": state["video_id"] or None,
    }
    save_transcription_content(state["user_id"], job_id, state["transcript"])
    collection_id = create_default_collection("transcriptions", job_id, metadata, state["user_id"])
    metadata["collection_id"] = collection_id  # lets the UI study this transcript on its own
    save_transcription_metadata(state["user_id"], job_id, metadata)
    return {"job_id": job_id, "metadata": metadata, "collection_id": collection_id}


def node_embed(state: MediaState) -> dict:
    _report("indexing")
    try:
        ingest_transcript(state["user_id"], state["job_id"], state["transcript"])
    except Exception as e:  # transcript is already saved; RAG is best-effort
        logger.warning(f"Embedding transcript {state['job_id']} failed: {e}")
    return {}


def build_media_graph():
    g = StateGraph(MediaState)
    g.add_node("acquire_audio", node_acquire_audio)
    g.add_node("transcribe", node_transcribe)
    g.add_node("store", node_store)
    g.add_node("embed", node_embed)

    g.set_entry_point("acquire_audio")
    g.add_edge("acquire_audio", "transcribe")
    g.add_edge("transcribe", "store")
    g.add_edge("store", "embed")
    g.add_edge("embed", END)
    return g.compile()


media_graph = build_media_graph()


def _run(source_type: str, user_id: str, title: str = "", source_url: Optional[str] = None,
         source_bytes: Optional[bytes] = None, filename: Optional[str] = None,
         on_progress: Optional[Callable[..., None]] = None) -> dict:
    with tempfile.TemporaryDirectory(prefix="learnai-media-") as work_dir:
        state = {
            "source_type": source_type, "source_url": source_url, "source_bytes": source_bytes,
            "filename": filename, "title": title, "user_id": user_id, "work_dir": work_dir,
            "audio_path": "", "video_id": "", "transcript": "", "job_id": "", "metadata": {},
            "collection_id": "",
        }
        for mode, chunk in media_graph.stream(state, stream_mode=["custom", "values"]):
            if mode == "values":
                result = chunk
            elif on_progress:
                on_progress(**chunk)
    return {"job_id": result["job_id"], "transcript": result["transcript"], "metadata": result["metadata"],
            "collection_id": result["collection_id"], "title": result["title"]}


def run_youtube_agent(video_url: str, user_id: str, on_progress: Optional[Callable[..., None]] = None) -> dict:
    """on_progress(stage=, progress=, title=) is called as the video downloads and transcribes."""
    return _run("youtube", user_id, source_url=video_url, on_progress=on_progress)


def run_lecture_agent(audio_bytes: bytes, filename: str, title: str, user_id: str) -> dict:
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_MEDIA_FORMATS:
        raise ValueError(f"Unsupported format {ext or '(none)'}. Supported: {sorted(SUPPORTED_MEDIA_FORMATS)}")
    return _run("upload", user_id, title=title, source_bytes=audio_bytes, filename=filename)
