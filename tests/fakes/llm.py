"""In-memory ``LLMClient`` stand-in for tests. Canned per-task responses,
validated against the *same* Pydantic schemas the real adapters use — a
schema change breaks the fake rather than production, matching the pattern
``tests/fakes/mongo.py`` uses for the database.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TypeVar

from pydantic import BaseModel

from learnai.config import LLMTask

BaseModelT = TypeVar("BaseModelT", bound=BaseModel)


@dataclass
class FakeLLMClient:
    completions: dict[LLMTask, str] = field(default_factory=dict)
    structured_responses: dict[LLMTask, BaseModel] = field(default_factory=dict)
    calls: list[dict[str, Any]] = field(default_factory=list)

    async def complete(self, *, task: LLMTask, prompt: str, system: str | None = None) -> str:
        self.calls.append({"task": task, "prompt": prompt, "system": system})
        return self.completions[task]

    async def structured(
        self, *, task: LLMTask, prompt: str, schema: type[BaseModelT], system: str | None = None
    ) -> BaseModelT:
        self.calls.append({"task": task, "prompt": prompt, "system": system})
        response = self.structured_responses[task]
        if not isinstance(response, schema):
            raise TypeError(f"fake structured response for {task} is not a {schema.__name__}")
        return response
