"""
LangGraph chat agent.
Pipeline: load_history → rag_retrieve → build_prompt → llm_call → save_history
"""
import logging
from typing import List

from langgraph.graph import StateGraph, END

from agents.base import ChatState
from core.llm import invoke_llm_with_history
from services.storage_service import load_chat_history, save_chat_history, load_extracted_text
from services.storage_service import load_narrative
from services.profile_service import get_learning_profile
from services.rag_service import retrieve_context
from services.accessibility_service import translate_text
from utils.prompt_utils import build_chat_prompt

logger = logging.getLogger(__name__)


def node_load_history(state: ChatState) -> ChatState:
    history = load_chat_history(state["user_id"], state["file_id"], state["section_name"])
    extracted_text = load_extracted_text(state["user_id"], state["file_id"], state["section_name"])
    narrative_data = load_narrative(state["user_id"], state["file_id"], state["section_name"], state["force_regenerate"])
    narrative_summary = narrative_data.get("narrative", "") if narrative_data else ""
    learning_profile = get_learning_profile(state["user_id"])
    return {**state, "history": history, "extracted_text": extracted_text,
            "narrative_summary": narrative_summary, "learning_profile": learning_profile}


def node_translate_input(state: ChatState) -> ChatState:
    if state["language"] == "en":
        return state
    translated = translate_text(state["user_message"], "en")
    if translated:
        return {**state, "user_message": translated}
    return state


def node_rag_retrieve(state: ChatState) -> ChatState:
    query = state["extracted_text"][:2000] if state["extracted_text"] else state["user_message"]
    context = retrieve_context(state["user_id"], query, file_id=state["file_id"])
    return {**state, "rag_context": context}


def node_llm_call(state: ChatState) -> ChatState:
    prompt = build_chat_prompt(
        state["user_message"],
        state["extracted_text"],
        state["narrative_summary"],
        state["rag_context"],
        state["learning_profile"],
    )
    lc_history = [
        {"role": "user" if m.get("user") == "You" else "assistant", "content": m.get("text", "")}
        for m in state["history"]
    ]
    try:
        response = invoke_llm_with_history(prompt, lc_history, max_tokens=500)
        return {**state, "ai_response": response}
    except Exception as e:
        logger.error(f"LLM call failed in chat agent: {e}")
        return {**state, "ai_response": "I'm sorry, I couldn't generate a response.", "error": str(e)}


def node_translate_output(state: ChatState) -> ChatState:
    if state["language"] == "en" or not state.get("ai_response"):
        return state
    translated = translate_text(state["ai_response"], state["language"])
    if translated:
        return {**state, "ai_response": translated}
    return state


def node_save_history(state: ChatState) -> ChatState:
    # Use original (non-translated) user message in history
    history = state["history"].copy()
    # Retrieve original message from messages if available
    history.append({"user": "You", "text": state.get("user_message", "")})
    history.append({"user": "AI", "text": state["ai_response"]})
    save_chat_history(state["user_id"], state["file_id"], state["section_name"], history)
    return state


def build_chat_graph():
    g = StateGraph(ChatState)
    g.add_node("load_history", node_load_history)
    g.add_node("translate_input", node_translate_input)
    g.add_node("rag_retrieve", node_rag_retrieve)
    g.add_node("llm_call", node_llm_call)
    g.add_node("translate_output", node_translate_output)
    g.add_node("save_history", node_save_history)

    g.set_entry_point("load_history")
    g.add_edge("load_history", "translate_input")
    g.add_edge("translate_input", "rag_retrieve")
    g.add_edge("rag_retrieve", "llm_call")
    g.add_edge("llm_call", "translate_output")
    g.add_edge("translate_output", "save_history")
    g.add_edge("save_history", END)
    return g.compile()


chat_graph = build_chat_graph()


def run_chat_agent(
    message: str,
    user_id: str,
    file_id: str,
    section_name: str,
    language: str = "en",
    force_regenerate: str = "false",
) -> str:
    from langchain_core.messages import HumanMessage
    initial: ChatState = {
        "messages": [HumanMessage(content=message)],
        "user_message": message,
        "user_id": user_id,
        "file_id": file_id,
        "section_name": section_name,
        "language": language,
        "force_regenerate": force_regenerate,
        "extracted_text": "",
        "narrative_summary": "",
        "rag_context": "",
        "learning_profile": "",
        "history": [],
        "ai_response": "",
        "error": None,
    }
    result = chat_graph.invoke(initial)
    return result["ai_response"]
