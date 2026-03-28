"""
AWS Bedrock client — the only remaining AWS dependency.
All Claude LLM calls go through this module via langchain-aws ChatBedrock.
"""
import json
import logging
from functools import lru_cache
from typing import AsyncGenerator, List

import boto3
from botocore.config import Config
from langchain_aws import ChatBedrock
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage

from core.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _bedrock_runtime_client():
    return boto3.client(
        service_name="bedrock-runtime",
        region_name=settings.AWS_DEFAULT_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        config=Config(retries={"max_attempts": 3}),
    )


def get_llm(model_id: str | None = None, streaming: bool = False) -> ChatBedrock:
    """Return a ChatBedrock instance for the given model."""
    return ChatBedrock(
        model_id=model_id or settings.BEDROCK_MODEL_HAIKU,
        client=_bedrock_runtime_client(),
        streaming=streaming,
        model_kwargs={"temperature": 0.7, "max_tokens": 8192},
    )


def get_sonnet(streaming: bool = False) -> ChatBedrock:
    return get_llm(settings.BEDROCK_MODEL_SONNET, streaming=streaming)


def get_haiku(streaming: bool = False) -> ChatBedrock:
    return get_llm(settings.BEDROCK_MODEL_HAIKU, streaming=streaming)


def invoke_llm(prompt: str, model_id: str | None = None, max_tokens: int = 8192) -> str:
    """Synchronous single-turn LLM call. Returns the full text response."""
    llm = get_llm(model_id)
    llm.model_kwargs = {"temperature": 0.7, "max_tokens": max_tokens}
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content


def invoke_llm_with_history(
    prompt: str,
    history: List[dict],
    model_id: str | None = None,
    max_tokens: int = 500,
) -> str:
    """Multi-turn LLM call with chat history. History items: {role: user|assistant, content: str}."""
    llm = get_llm(model_id)
    llm.model_kwargs = {"temperature": 0.7, "max_tokens": max_tokens}

    messages: List[BaseMessage] = []
    for msg in history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))
    messages.append(HumanMessage(content=prompt))

    response = llm.invoke(messages)
    return response.content


async def stream_llm(
    prompt: str,
    model_id: str | None = None,
    max_tokens: int = 8192,
) -> AsyncGenerator[str, None]:
    """Async generator that streams text tokens from the LLM."""
    llm = get_llm(model_id, streaming=True)
    llm.model_kwargs = {"temperature": 0.7, "max_tokens": max_tokens}

    async for chunk in llm.astream([HumanMessage(content=prompt)]):
        if chunk.content:
            yield chunk.content


async def stream_llm_with_history(
    prompt: str,
    history: List[dict],
    model_id: str | None = None,
    max_tokens: int = 500,
) -> AsyncGenerator[str, None]:
    """Streaming multi-turn LLM call."""
    llm = get_llm(model_id, streaming=True)
    llm.model_kwargs = {"temperature": 0.7, "max_tokens": max_tokens}

    messages: List[BaseMessage] = []
    for msg in history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))
    messages.append(HumanMessage(content=prompt))

    async for chunk in llm.astream(messages):
        if chunk.content:
            yield chunk.content
