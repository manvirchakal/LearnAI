"""
LangGraph chat agent — tutoring chat grounded in one study unit.

    load_context ▶ translate_input ▶ rag_retrieve ▶ llm_call ▶ translate_output ▶ save_history ▶ END

History is persisted per (scope, unit_id) as [{"role": "user"|"assistant", "content": str}].
"""
import logging
from typing import Dict, List, Optional

from langgraph.graph import END, StateGraph

from agents.base import ChatState
from core.llm import invoke_llm_with_history
from services.accessibility_service import translate_text
from services.profile_service import get_learning_profile
from services.rag_service import retrieve_context
from services.storage_service import load_chat_history, load_study_materials, save_chat_history
from utils.prompt_utils import build_chat_prompt

logger = logging.getLogger(__name__)

HISTORY_WINDOW = 20  # messages sent to the model; full history is still stored


def node_load_context(state: ChatState) -> dict:
    materials = load_study_materials(state["user_id"], state["scope"], state["unit_id"])
    return {
        "history": load_chat_history(state["user_id"], state["scope"], state["unit_id"]),
        "narrative_summary": materials.get("narrative", ""),
        "learning_profile": get_learning_profile(state["user_id"]),
    }


def node_translate_input(state: ChatState) -> dict:
    if state["language"] == "en":
        return {"query_message": state["user_message"]}
    return {"query_message": translate_text(state["user_message"], "en", source_language=state["language"]) or state["user_message"]}


def node_rag_retrieve(state: ChatState) -> dict:
    context = retrieve_context(state["user_id"], state["query_message"], file_id=state["rag_file_id"])
    return {"rag_context": context}


def node_llm_call(state: ChatState) -> dict:
    prompt = build_chat_prompt(
        state["query_message"],
        state["context_text"],
        state["narrative_summary"],
        state["rag_context"],
        state["learning_profile"],
    )
    try:
        reply = invoke_llm_with_history(prompt, state["history"][-HISTORY_WINDOW:], max_tokens=1024)
        return {"ai_response": reply}
    except Exception as e:
        logger.error(f"LLM call failed in chat agent: {e}")
        return {"ai_response": "Sorry, I couldn't generate a response. Please try again.", "error": str(e)}


def node_translate_output(state: ChatState) -> dict:
    if state["language"] == "en" or state.get("error"):
        return {}
    return {"ai_response": translate_text(state["ai_response"], state["language"]) or state["ai_response"]}


def node_save_history(state: ChatState) -> dict:
    if state.get("error"):
        return {}  # don't persist failed turns
    history = state["history"] + [
        {"role": "user", "content": state["user_message"]},
        {"role": "assistant", "content": state["ai_response"]},
    ]
    save_chat_history(state["user_id"], state["scope"], state["unit_id"], history)
    return {"history": history}


def build_chat_graph():
    g = StateGraph(ChatState)
    g.add_node("load_context", node_load_context)
    g.add_node("translate_input", node_translate_input)
    g.add_node("rag_retrieve", node_rag_retrieve)
    g.add_node("llm_call", node_llm_call)
    g.add_node("translate_output", node_translate_output)
    g.add_node("save_history", node_save_history)

    g.set_entry_point("load_context")
    g.add_edge("load_context", "translate_input")
    g.add_edge("translate_input", "rag_retrieve")
    g.add_edge("rag_retrieve", "llm_call")
    g.add_edge("llm_call", "translate_output")
    g.add_edge("translate_output", "save_history")
    g.add_edge("save_history", END)
    return g.compile()


chat_graph = build_chat_graph()


def get_history(user_id: str, scope: str, unit_id: str) -> List[Dict]:
    return load_chat_history(user_id, scope, unit_id)


def run_chat_agent(message: str, context_text: str, user_id: str, scope: str, unit_id: str,
                   rag_file_id: Optional[str] = None, language: str = "en") -> Dict:
    """Answer one chat turn. Returns {"reply", "history"}."""
    initial: ChatState = {
        "user_message": message,
        "query_message": message,
        "user_id": user_id,
        "scope": scope,
        "unit_id": unit_id,
        "rag_file_id": rag_file_id,
        "language": language,
        "context_text": context_text,
        "narrative_summary": "",
        "rag_context": "",
        "learning_profile": "",
        "history": [],
        "ai_response": "",
        "error": None,
    }
    result = chat_graph.invoke(initial)
    if result.get("error"):
        raise RuntimeError(result["error"])
    return {"reply": result["ai_response"], "history": result["history"]}
