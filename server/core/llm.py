"""
AWS Bedrock client — the only remaining AWS dependency.
All Claude LLM calls go through this module via langchain-aws ChatBedrock.
"""
import logging
from functools import lru_cache
from typing import List

import boto3
from botocore.config import Config
from langchain_aws import ChatBedrock
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from core.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _bedrock_runtime_client():
    return boto3.client(
        service_name="bedrock-runtime",
        region_name=settings.AWS_DEFAULT_REGION,
        # None (not "") lets boto3 fall back to its credential chain (env, profile, SSO, role)
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None,
        config=Config(retries={"max_attempts": 3}),
    )


def get_llm(model_id: str | None = None, max_tokens: int = 4096, temperature: float = 0.7) -> BaseChatModel:
    """Chat model for the given Bedrock model id (Haiku by default)."""
    return ChatBedrock(
        model_id=model_id or settings.BEDROCK_MODEL_HAIKU,
        client=_bedrock_runtime_client(),
        max_tokens=max_tokens,
        temperature=temperature,
    )


def get_sonnet(max_tokens: int = 4096) -> BaseChatModel:
    return get_llm(settings.BEDROCK_MODEL_SONNET, max_tokens=max_tokens)


def get_haiku(max_tokens: int = 4096) -> BaseChatModel:
    return get_llm(settings.BEDROCK_MODEL_HAIKU, max_tokens=max_tokens)


def message_text(message: BaseMessage) -> str:
    """Plain text of a message whose content may be a string or content blocks."""
    content = message.content
    if isinstance(content, str):
        return content
    return "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in content)


def invoke_llm(prompt: str, model_id: str | None = None, max_tokens: int = 8192) -> str:
    """Single-turn call. Inside a LangGraph run streamed with stream_mode="messages",
    tokens are streamed to the graph's consumer automatically via callbacks."""
    return message_text(get_llm(model_id, max_tokens).invoke([HumanMessage(content=prompt)]))


def invoke_llm_with_history(
    prompt: str,
    history: List[dict],
    model_id: str | None = None,
    max_tokens: int = 1024,
) -> str:
    """Multi-turn call. History items: {"role": "user"|"assistant", "content": str}."""
    messages: List[BaseMessage] = [
        HumanMessage(content=m["content"]) if m["role"] == "user" else AIMessage(content=m["content"])
        for m in history
    ]
    messages.append(HumanMessage(content=prompt))
    return message_text(get_llm(model_id, max_tokens).invoke(messages))
