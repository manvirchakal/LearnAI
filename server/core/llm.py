"""
Chat model factory. Every LLM call in the app goes through get_llm().

Providers (settings.LLM_PROVIDER):
    openai   any OpenAI-compatible server — vLLM on the local network in production
    bedrock  Claude via AWS Bedrock
"""
import logging
import re
from functools import lru_cache
from typing import Literal, Sequence, Union

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage

from core.config import settings

logger = logging.getLogger(__name__)

Role = Literal["text", "vision"]

_BEDROCK_DEFAULTS = {
    "text": "us.anthropic.claude-3-5-haiku-20241022-v1:0",
    "vision": "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
}


@lru_cache(maxsize=1)
def _bedrock_runtime_client():
    import boto3
    from botocore.config import Config

    return boto3.client(
        service_name="bedrock-runtime",
        region_name=settings.AWS_DEFAULT_REGION,
        # None (not "") lets boto3 fall back to its credential chain (env, profile, SSO, role)
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None,
        config=Config(retries={"max_attempts": 3}, read_timeout=settings.LLM_TIMEOUT_SECONDS),
    )


@lru_cache(maxsize=1)
def _served_model() -> str:
    """The first model an OpenAI-compatible server lists (vLLM serves exactly one)."""
    from openai import OpenAI

    models = OpenAI(base_url=settings.OPENAI_BASE_URL, api_key=settings.OPENAI_API_KEY, timeout=10).models.list()
    if not models.data:
        raise RuntimeError(f"No models served at {settings.OPENAI_BASE_URL}")
    logger.info(f"Using served model {models.data[0].id}")
    return models.data[0].id


def model_name(role: Role = "text") -> str:
    configured = settings.LLM_VISION_MODEL if role == "vision" else ""
    configured = configured or settings.LLM_MODEL
    if configured:
        return configured
    return _BEDROCK_DEFAULTS[role] if settings.LLM_PROVIDER == "bedrock" else _served_model()


def get_llm(role: Role = "text", max_tokens: int = 4096, temperature: float = 1.0) -> BaseChatModel:
    """Chat model for a role, with max_tokens capped at settings.max_output_tokens."""
    max_tokens = min(max_tokens, settings.max_output_tokens)
    if settings.LLM_PROVIDER == "bedrock":
        from langchain_aws import ChatBedrock

        return ChatBedrock(model_id=model_name(role), client=_bedrock_runtime_client(),
                           max_tokens=max_tokens, temperature=temperature)

    from langchain_openai import ChatOpenAI

    return ChatOpenAI(model=model_name(role), base_url=settings.OPENAI_BASE_URL, api_key=settings.OPENAI_API_KEY,
                      max_tokens=max_tokens, temperature=temperature,
                      timeout=settings.LLM_TIMEOUT_SECONDS, max_retries=2)


_THINK = re.compile(r"<think>.*?</think>\s*", re.DOTALL)


def message_text(message: BaseMessage) -> str:
    """Plain text of a message whose content may be a string or content blocks.
    Reasoning blocks some open models emit inline (<think>…</think>) are dropped."""
    content = message.content
    if not isinstance(content, str):
        content = "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in content)
    return _THINK.sub("", content)


def image_block(data_b64: str, media_type: str = "image/jpeg") -> dict:
    """An image content block both providers accept (OpenAI data-URL format)."""
    return {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{data_b64}"}}


def invoke_llm(prompt: Union[str, Sequence[BaseMessage]], max_tokens: int = 8192, role: Role = "text") -> str:
    """Reply to a prompt, or continue a conversation given as messages (ending
    with the human turn to answer). Inside a LangGraph run streamed with
    stream_mode="messages", tokens are streamed to the graph's consumer
    automatically via callbacks."""
    messages = [HumanMessage(content=prompt)] if isinstance(prompt, str) else list(prompt)
    return message_text(get_llm(role, max_tokens).invoke(messages))

