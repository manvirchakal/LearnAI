"""Provider-agnostic generation client: one narrow ``Protocol`` both backends
implement, matching the pattern already used for ``StorageBackend`` in
``services/storage/base.py``.

Deliberately hand-rolled rather than a third-party unification library (e.g.
LiteLLM) — that keeps full control over structured-output and refusal
handling and avoids an abstraction-over-our-abstraction. This does not
cover ingestion: ``DocumentExtractor`` (native PDF ``document`` blocks,
citations, the Files API) has no OpenAI-compatible equivalent and stays
Anthropic-only on its own Protocol.

``complete()``, ``structured()``, and ``stream()`` exist here because
those are the callers this codebase has today (profile-description
generation, and now narrative/game/diagram generation). ``agent()`` (the
ReAct chat agent) lands with Phase 6, the phase that actually needs it —
adding it now, with no caller and nothing to test against, would be
exactly the premature abstraction the rest of this codebase avoids.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol, TypeVar

from pydantic import BaseModel

from learnai.config import LLMTask

BaseModelT = TypeVar("BaseModelT", bound=BaseModel)


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
