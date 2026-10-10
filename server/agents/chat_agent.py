"""
LangGraph chat agent — tutoring chat grounded in one study unit.

    load_context ▶ translate_input ▶ tutor ▶ translate_output ▶ save_history ▶ END

tutor is a LangChain ReAct agent (create_agent): it answers, calling TUTOR_TOOLS
(agents/tutor_tools.py) to search and read the student's materials as it sees
fit. Its system prompt lists the unit's sources (ids, titles, lengths) for the
tools, with the unit's summary and the learning profile.

History is persisted per (scope, unit_id) as [{"role": "user"|"assistant", "content": str}].
"""
import logging
from typing import AsyncIterator, Dict, List, Optional, Tuple

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

import core.llm
from agents.base import ChatState
from agents.tutor_tools import TUTOR_TOOLS, TutorContext
from core.llm import message_text
from services.accessibility_service import translate_text
from services.profile_service import get_learning_profile
from services.rag_service import parse_source, section_text
from services.storage_service import load_chat_history, load_study_materials, save_chat_history
from utils.prompt_utils import build_chat_system_prompt

logger = logging.getLogger(__name__)

HISTORY_WINDOW = 20  # messages sent to the model; full history is still stored
MAX_REPLY_TOKENS = 1024
REPLY_SEPARATOR = "\n\n"  # between texts the tutor writes in separate steps of one turn


def build_tutor_agent():
    return create_agent(core.llm.get_llm(max_tokens=MAX_REPLY_TOKENS), tools=TUTOR_TOOLS,
                        context_schema=TutorContext, name="tutor")


def tutor_messages(state: ChatState) -> List[BaseMessage]:
    system = build_chat_system_prompt(
        state["sources"],
        state["narrative_summary"],
        state["learning_profile"],
    )
    history = [
        HumanMessage(content=m["content"]) if m["role"] == "user" else AIMessage(content=m["content"])
        for m in state["history"][-HISTORY_WINDOW:]
    ]
    return [SystemMessage(content=system), *history, HumanMessage(content=state["query_message"])]


def node_load_context(state: ChatState) -> dict:
    materials = load_study_materials(state["user_id"], state["scope"], state["unit_id"])
    sources = []
    for s in state["sources"]:
        text = section_text(state["user_id"], *parse_source(s["source"]))
        if text:  # only what the tutor can read
            sources.append({**s, "length": len(text)})
    return {
        "sources": sources,
        "history": load_chat_history(state["user_id"], state["scope"], state["unit_id"]),
        "narrative_summary": materials.get("narrative", ""),
        "learning_profile": get_learning_profile(state["user_id"]),
    }


def node_translate_input(state: ChatState) -> dict:
    if state["language"] == "en":
        return {"query_message": state["user_message"]}
    return {"query_message": translate_text(state["user_message"], "en", source_language=state["language"]) or state["user_message"]}


def node_tutor(state: ChatState) -> dict:
    try:
        # A book chat sees the whole book; a collection chat, the collection's sources
        context = TutorContext(state["user_id"], file_id=state["rag_file_id"],
                               sources=[s["source"] for s in state["sources"]])
        messages = tutor_messages(state)
        result = build_tutor_agent().invoke({"messages": messages}, context=context)
        # Text the tutor wrote alongside tool calls was streamed too, so it's part of the reply
        replies = [message_text(m) for m in result["messages"][len(messages):] if isinstance(m, AIMessage)]
        return {"ai_response": REPLY_SEPARATOR.join(r for r in replies if r)}
    except Exception as e:
        logger.error(f"Tutor agent failed in chat agent: {e}")
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
    g.add_node("tutor", node_tutor)
    g.add_node("translate_output", node_translate_output)
    g.add_node("save_history", node_save_history)

    g.set_entry_point("load_context")
    g.add_edge("load_context", "translate_input")
    g.add_edge("translate_input", "tutor")
    g.add_edge("tutor", "translate_output")
    g.add_edge("translate_output", "save_history")
    g.add_edge("save_history", END)
    return g.compile()


chat_graph = build_chat_graph()


def get_history(user_id: str, scope: str, unit_id: str) -> List[Dict]:
    return load_chat_history(user_id, scope, unit_id)


def _initial_state(message: str, sources: List[Dict[str, str]], user_id: str, scope: str, unit_id: str,
                   rag_file_id: Optional[str], language: str) -> ChatState:
    return {
        "user_message": message,
        "query_message": message,
        "user_id": user_id,
        "scope": scope,
        "unit_id": unit_id,
        "rag_file_id": rag_file_id,
        "sources": sources,
        "language": language,
        "narrative_summary": "",
        "learning_profile": "",
        "history": [],
        "ai_response": "",
        "error": None,
    }


def run_chat_agent(message: str, sources: List[Dict[str, str]], user_id: str, scope: str, unit_id: str,
                   rag_file_id: Optional[str] = None, language: str = "en") -> Dict:
    """Answer one chat turn. Returns {"reply", "history"}."""
    result = chat_graph.invoke(_initial_state(message, sources, user_id, scope, unit_id, rag_file_id, language))
    if result.get("error"):
        raise RuntimeError(result["error"])
    return {"reply": result["ai_response"], "history": result["history"]}


async def stream_chat_agent(message: str, sources: List[Dict[str, str]], user_id: str, scope: str, unit_id: str,
                            rag_file_id: Optional[str] = None,
                            language: str = "en") -> AsyncIterator[Tuple[str, str]]:
    """
    Answer one chat turn, yielding events as they happen:
        ("stage", str)   a graph node finished, or the tutor called a tool (its name)
        ("token", str)   reply text as the model writes it
    In English the reply streams token by token; otherwise it's translated
    after generation and arrives as one token. Raises if the turn failed.
    """
    state = _initial_state(message, sources, user_id, scope, unit_id, rag_file_id, language)
    stream_tokens = language == "en"
    replying_to = None  # id of the tutor message whose text is streaming
    # subgraphs=True streams the tutor agent's model tokens, tagged with its namespace
    async for namespace, mode, chunk in chat_graph.astream(state, stream_mode=["messages", "updates"],
                                                           subgraphs=True):
        if mode == "messages":
            msg, meta = chunk
            if stream_tokens and isinstance(msg, AIMessageChunk) and meta.get("lc_agent_name") == "tutor":
                token = message_text(msg)
                if token:
                    if replying_to not in (None, msg.id):
                        yield "token", REPLY_SEPARATOR  # text from a later step, as in node_tutor
                    replying_to = msg.id
                    yield "token", token
            continue
        if namespace:
            for message in (chunk.get("model") or {}).get("messages", []):
                for call in getattr(message, "tool_calls", []):
                    yield "stage", call["name"]
            if "tools" in chunk:
                yield "stage", "tools"
            continue
        for node, update in chunk.items():
            if (update or {}).get("error"):
                raise RuntimeError(update["error"])
            yield "stage", node
            if node == "translate_output" and not stream_tokens:
                yield "token", (update or {}).get("ai_response") or ""
