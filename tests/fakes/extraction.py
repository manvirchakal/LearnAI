"""In-memory ``DocumentExtractor`` stand-in for tests — no real Anthropic
Files API or PDF-reading call, validated against the same Pydantic schemas
the real extractor returns (matching ``tests/fakes/llm.py``'s pattern).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from learnai.schemas.documents import SectionContent, TOCResult
from learnai.services.extraction.base import DocRef


@dataclass
class FakeExtractor:
    toc_result: TOCResult | None = None
    section_results: dict[str, SectionContent] = field(default_factory=dict)
    calls: list[dict[str, Any]] = field(default_factory=list)

    async def upload(self, pdf_bytes: bytes, *, filename: str) -> DocRef:
        self.calls.append({"op": "upload", "filename": filename})
        return DocRef(file_id="fake-file-id")

    async def delete(self, ref: DocRef) -> None:
        self.calls.append({"op": "delete", "file_id": ref.file_id})

    async def extract_toc(self, ref: DocRef, *, page_offset: int = 0) -> TOCResult:
        self.calls.append({"op": "extract_toc", "file_id": ref.file_id})
        assert self.toc_result is not None, "FakeExtractor.toc_result was not configured"
        return self.toc_result

    async def extract_section(
        self, ref: DocRef, *, node_id: str, page_offset: int = 0
    ) -> SectionContent:
        self.calls.append({"op": "extract_section", "file_id": ref.file_id, "node_id": node_id})
        return self.section_results[node_id]
