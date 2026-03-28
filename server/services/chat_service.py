"""
Chat service — history management, context assembly, and response generation.
"""
import logging
from typing import List

from services.storage_service import save_chat_history, load_chat_history, load_extracted_text
from services.rag_service import retrieve_context
from services.profile_service import get_learning_profile
from core.llm import invoke_llm_with_history
from utils.prompt_utils import build_chat_prompt

logger = logging.getLogger(__name__)


def get_chat_history(user_id: str, file_id: str, section_name: str) -> List[dict]:
    return load_chat_history(user_id, file_id, section_name)


def _history_to_langchain_format(history: List[dict]) -> List[dict]:
    """Convert [{user: "You", text: "..."}, ...] → [{role: ..., content: ...}]."""
    result = []
    for msg in history:
        role = "user" if msg.get("user") == "You" else "assistant"
        result.append({"role": role, "content": msg.get("text", "")})
    return result


def send_message(
    user_message: str,
    user_id: str,
    file_id: str,
    section_name: str,
    language: str = "en",
    force_regenerate: str = "false",
) -> str:
    """
    Core chat logic:
    1. Load extracted text + narrative as context
    2. Retrieve RAG context from ChromaDB
    3. Build prompt and call Claude
    4. Optionally translate response
    5. Append to history and persist
    """
    extracted_text = load_extracted_text(user_id, file_id, section_name)

    # Load cached narrative summary if it exists
    from services.storage_service import load_narrative
    narrative_data = load_narrative(user_id, file_id, section_name, force_regenerate)
    generated_summary = narrative_data.get("narrative", "") if narrative_data else ""

    rag_context = retrieve_context(user_id, extracted_text[:2000] if extracted_text else user_message, file_id=file_id)
    learning_profile = get_learning_profile(user_id)

    # Translate incoming message to English if needed
    effective_message = user_message
    if language != "en":
        from services.accessibility_service import translate_text
        effective_message = translate_text(user_message, "en") or user_message

    prompt = build_chat_prompt(
        effective_message, extracted_text, generated_summary, rag_context, learning_profile
    )

    history = load_chat_history(user_id, file_id, section_name)
    lc_history = _history_to_langchain_format(history)

    ai_response = invoke_llm_with_history(prompt, lc_history, max_tokens=500)

    # Translate response back if needed
    if language != "en":
        from services.accessibility_service import translate_text
        ai_response = translate_text(ai_response, language) or ai_response

    # Persist history
    history.append({"user": "You", "text": user_message})
    history.append({"user": "AI", "text": ai_response})
    save_chat_history(user_id, file_id, section_name, history)

    return ai_response
