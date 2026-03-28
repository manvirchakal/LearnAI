"""
LangGraph media ingestion agent.
Pipeline: download_or_buffer → transcribe_whisper → store → embed
"""
import asyncio
import logging
import os
import uuid
from datetime import datetime
from typing import Optional

from langgraph.graph import StateGraph, END

from agents.base import MediaState
from services.storage_service import save_transcription_metadata, save_transcription_content
from services.collection_service import create_default_collection
from services.rag_service import ingest_transcript
from services.media_service import _transcribe_file, _convert_to_mp3, SUPPORTED_MEDIA_FORMATS

logger = logging.getLogger(__name__)


def node_download_or_buffer(state: MediaState) -> MediaState:
    """For YouTube: download audio to /tmp. For uploads: bytes already in state."""
    if state["source_type"] == "youtube":
        from yt_dlp import YoutubeDL
        job_id = str(uuid.uuid4())
        temp_path = f"/tmp/{job_id}"
        ydl_opts = {
            "format": "bestaudio/best",
            "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}],
            "outtmpl": temp_path,
            "quiet": True,
            "no_warnings": True,
        }
        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(state["source_url"], download=True)
                title = info.get("title", "Untitled Video")
            mp3_path = f"{temp_path}.mp3"
            return {**state, "filename": mp3_path, "title": title, "job_id": job_id}
        except Exception as e:
            return {**state, "error": str(e)}
    else:
        # Upload: write bytes to temp file
        job_id = str(uuid.uuid4())
        orig_ext = os.path.splitext(state.get("filename", ".mp3"))[1].lower()
        temp_input = f"/tmp/{job_id}_input{orig_ext}"
        temp_mp3 = f"/tmp/{job_id}.mp3"
        with open(temp_input, "wb") as f:
            f.write(state["source_bytes"])
        if orig_ext != ".mp3":
            try:
                _convert_to_mp3(temp_input, temp_mp3)
                os.remove(temp_input)
                return {**state, "filename": temp_mp3, "job_id": job_id}
            except Exception as e:
                return {**state, "error": str(e)}
        else:
            os.rename(temp_input, temp_mp3)
            return {**state, "filename": temp_mp3, "job_id": job_id}


def node_transcribe(state: MediaState) -> MediaState:
    if state.get("error"):
        return state
    try:
        transcript = _transcribe_file(state["filename"])
        return {**state, "transcript": transcript}
    except Exception as e:
        return {**state, "error": str(e), "transcript": ""}
    finally:
        # Clean up temp audio
        try:
            if state.get("filename") and os.path.exists(state["filename"]):
                os.remove(state["filename"])
        except Exception:
            pass


def node_store(state: MediaState) -> MediaState:
    if state.get("error"):
        return state
    job_id = state.get("job_id", str(uuid.uuid4()))
    metadata = {
        "job_id": job_id,
        "title": state.get("title", "Untitled"),
        "original_filename": state.get("title", "Untitled"),
        "transcription_date": datetime.now().isoformat(),
        "source_type": state["source_type"],
        "video_url": state.get("source_url"),
    }
    save_transcription_metadata(state["user_id"], job_id, metadata)
    save_transcription_content(state["user_id"], job_id, state["transcript"])
    collection_id = create_default_collection("transcriptions", job_id, metadata, state["user_id"])
    return {**state, "job_id": job_id, "collection_id": collection_id}


def node_embed(state: MediaState) -> MediaState:
    if state.get("error") or not state.get("transcript"):
        return state
    try:
        ingest_transcript(state["user_id"], state["job_id"], state["transcript"])
    except Exception as e:
        logger.warning(f"Embedding failed for transcript {state.get('job_id')}: {e}")
    return state


def build_media_graph():
    g = StateGraph(MediaState)
    g.add_node("download_or_buffer", node_download_or_buffer)
    g.add_node("transcribe", node_transcribe)
    g.add_node("store", node_store)
    g.add_node("embed", node_embed)

    g.set_entry_point("download_or_buffer")
    g.add_edge("download_or_buffer", "transcribe")
    g.add_edge("transcribe", "store")
    g.add_edge("store", "embed")
    g.add_edge("embed", END)
    return g.compile()


media_graph = build_media_graph()


async def run_media_agent_youtube(video_url: str, user_id: str) -> dict:
    initial: MediaState = {
        "source_type": "youtube",
        "source_url": video_url,
        "source_bytes": None,
        "filename": None,
        "title": None,
        "user_id": user_id,
        "transcript": "",
        "job_id": "",
        "collection_id": "",
        "error": None,
    }
    result = await asyncio.get_event_loop().run_in_executor(None, media_graph.invoke, initial)
    if result.get("error"):
        raise RuntimeError(result["error"])
    return result


async def run_media_agent_upload(audio_bytes: bytes, filename: str, title: str, user_id: str) -> dict:
    initial: MediaState = {
        "source_type": "upload",
        "source_url": None,
        "source_bytes": audio_bytes,
        "filename": filename,
        "title": title,
        "user_id": user_id,
        "transcript": "",
        "job_id": "",
        "collection_id": "",
        "error": None,
    }
    result = await asyncio.get_event_loop().run_in_executor(None, media_graph.invoke, initial)
    if result.get("error"):
        raise RuntimeError(result["error"])
    return result
