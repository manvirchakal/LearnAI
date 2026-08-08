"""Provider-agnostic generation client: one narrow ``Protocol`` both backends
implement, matching the pattern already used for ``StorageBackend`` in
``services/storage/base.py``.

Deliberately hand-rolled rather than a third-party unification library (e.g.
LiteLLM) — that keeps full control over structured-output and refusal
handling and avoids an abstraction-over-our-abstraction. This does not
cover ingestion: ``DocumentExtractor`` (native PDF ``document`` blocks,
citations, the Files API) has no OpenAI-compatible equivalent and stays
Anthropic-only on its own Protocol.

Only ``complete()`` and ``structured()`` exist here because those are the
only two callers this codebase has today (profile-description generation).
``stream()`` (SSE narrative streaming) and ``agent()`` (the ReAct chat
agent) land with the phases that actually need them — adding them now,
with no caller and nothing to test against, would be exactly the
premature abstraction the rest of this codebase avoids.
"""

from __future__ import annotations

from typing import Protocol, TypeVar

from pydantic import BaseModel

from learnai.config import LLMTask

BaseModelT = TypeVar("BaseModelT", bound=BaseModel)


class LLMClient(Protocol):
    async def complete(self, *, task: LLMTask, prompt: str, system: str | None = None) -> str: ...

    async def structured(
        self, *, task: LLMTask, prompt: str, schema: type[BaseModelT], system: str | None = None
    ) -> BaseModelT: ...
