"""In-memory ``LLMClient`` stand-in for tests. Canned per-task responses,
validated against the *same* Pydantic schemas the real adapters use — a
schema change breaks the fake rather than production, matching the pattern
``tests/fakes/mongo.py`` uses for the database.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, TypeVar

from pydantic import BaseModel

from learnai.config import LLMTask
from learnai.services.llm.client import AgentResult, AgentTool, AgentToolCall

BaseModelT = TypeVar("BaseModelT", bound=BaseModel)


@dataclass
class FakeLLMClient:
    completions: dict[LLMTask, str] = field(default_factory=dict)
    structured_responses: dict[LLMTask, BaseModel] = field(default_factory=dict)
    # For a caller that makes more than one structured() call for the same
    # task and needs a different response each time (e.g. a validate-then-
    # repair round trip) — checked first, popped in order; falls back to
    # structured_responses (a fixed response reused every call) once
    # exhausted or if never set for that task.
    structured_response_queue: dict[LLMTask, list[BaseModel]] = field(default_factory=dict)
    stream_chunks: dict[LLMTask, list[str]] = field(default_factory=dict)
    agent_responses: dict[LLMTask, str] = field(default_factory=dict)
    # Tool calls the fake makes (by name, with raw arguments validated
    # against the matching AgentTool's schema) before returning
    # agent_responses[task] — lets a test exercise the citations-from-
    # search_materials pipeline without a real model deciding to call one.
    agent_tool_calls: dict[LLMTask, list[tuple[str, dict[str, Any]]]] = field(default_factory=dict)
    calls: list[dict[str, Any]] = field(default_factory=list)

    async def complete(self, *, task: LLMTask, prompt: str, system: str | None = None) -> str:
        self.calls.append({"task": task, "prompt": prompt, "system": system})
        return self.completions[task]

    async def structured(
        self, *, task: LLMTask, prompt: str, schema: type[BaseModelT], system: str | None = None
    ) -> BaseModelT:
        self.calls.append({"task": task, "prompt": prompt, "system": system})
        queue = self.structured_response_queue.get(task)
        response = queue.pop(0) if queue else self.structured_responses[task]
        if not isinstance(response, schema):
            raise TypeError(f"fake structured response for {task} is not a {schema.__name__}")
        return response

    def stream(
        self, *, task: LLMTask, prompt: str, system: str | None = None
    ) -> AsyncIterator[str]:
        self.calls.append({"task": task, "prompt": prompt, "system": system})
        return self._stream(task)

    async def _stream(self, task: LLMTask) -> AsyncIterator[str]:
        for chunk in self.stream_chunks[task]:
            yield chunk

    async def agent(
        self,
        *,
        task: LLMTask,
        system: str,
        messages: list[dict[str, str]],
        tools: list[AgentTool],
        max_iterations: int = 8,
    ) -> AgentResult:
        self.calls.append({"task": task, "system": system, "messages": messages})
        tool_by_name = {tool.name: tool for tool in tools}
        tool_calls: list[AgentToolCall] = []
        for name, raw_arguments in self.agent_tool_calls.get(task, []):
            tool = tool_by_name[name]
            arguments = tool.args_schema.model_validate(raw_arguments).model_dump(mode="json")
            result = await tool.handler(**arguments)
            tool_calls.append(AgentToolCall(tool_name=name, arguments=arguments, result=result))
        return AgentResult(text=self.agent_responses[task], tool_calls=tool_calls)
