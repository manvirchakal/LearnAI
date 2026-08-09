"""Provider-agnostic generation client: one narrow ``Protocol`` both backends
implement, matching the pattern already used for ``StorageBackend`` in
``services/storage/base.py``.

Deliberately hand-rolled rather than a third-party unification library (e.g.
LiteLLM) — that keeps full control over structured-output and refusal
handling and avoids an abstraction-over-our-abstraction. This does not
cover ingestion: ``DocumentExtractor`` (native PDF ``document`` blocks,
citations, the Files API) has no OpenAI-compatible equivalent and stays
Anthropic-only on its own Protocol.

``agent()`` is the ReAct chat agent (Phase 6). ``AgentTool`` is our own
tiny tool abstraction rather than either backend's native tool type: a
name, a description, a Pydantic args schema (doubles as the JSON schema
sent to the model and as real argument validation before ``handler``
runs), and an async ``handler``. Both adapters build their own
backend-specific tool representation from this at call time — the
Anthropic adapter wraps each one for ``client.beta.messages.tool_runner``,
the OpenAI-compatible adapter turns it into a Chat Completions ``tools``
entry for its own manual loop — so callers (``services/agent/tools.py``)
never import either SDK.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

from learnai.config import LLMTask

BaseModelT = TypeVar("BaseModelT", bound=BaseModel)


@dataclass(frozen=True)
class AgentTool:
    name: str
    description: str
    args_schema: type[BaseModel]
    handler: Callable[..., Awaitable[str]]


@dataclass(frozen=True)
class AgentToolCall:
    tool_name: str
    arguments: dict[str, Any]
    result: str


@dataclass(frozen=True)
class AgentResult:
    text: str
    tool_calls: list[AgentToolCall] = field(default_factory=list)


class LLMClient(Protocol):
    async def complete(self, *, task: LLMTask, prompt: str, system: str | None = None) -> str: ...

    async def structured(
        self, *, task: LLMTask, prompt: str, schema: type[BaseModelT], system: str | None = None
    ) -> BaseModelT: ...

    def stream(
        self, *, task: LLMTask, prompt: str, system: str | None = None
    ) -> AsyncIterator[str]:
        """Yields text deltas as they arrive — narrative generation streams
        to the client over SSE rather than waiting for the full response.

        Not ``async def`` — called (not awaited) to get an async iterator,
        then consumed with ``async for chunk in client.stream(...)``, the
        same pattern ``StorageBackend.open()`` uses for the same reason.
        """
        ...

    async def agent(
        self,
        *,
        task: LLMTask,
        system: str,
        messages: list[dict[str, str]],
        tools: list[AgentTool],
        max_iterations: int = 8,
    ) -> AgentResult:
        """Runs a tool-using ReAct loop to completion and returns the final
        text plus every tool call made along the way (the caller uses the
        latter to build citations — see ``services/agent/chat_agent.py``).

        ``messages`` is plain ``{"role": "user" | "assistant", "content":
        str}`` turns — prior conversation history plus the new user
        message, already appended by the caller. The tool-calling loop
        itself (and any backend-specific message shape it needs along the
        way) is entirely internal to the adapter; nothing about it is
        exposed here, which is what keeps this Protocol implementable by
        an OpenAI-compatible backend at all.
        """
        ...
