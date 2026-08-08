"""Document extraction: native-PDF reading for the TOC pass and lazy
per-section extraction.

Anthropic-only — native PDF ``document`` content blocks, citations, and the
Files API are Anthropic-specific mechanics with no OpenAI-compatible
equivalent — so this sits behind its own Protocol, independent of the
provider-agnostic generation ``LLMClient`` in ``services/llm/``. A future
``VLMExtractor`` (rasterize via PyMuPDF → image blocks → any vision model)
would implement the same Protocol.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from learnai.schemas.documents import SectionContent, TOCResult


@dataclass(frozen=True, slots=True)
class DocRef:
    """An uploaded document, opaque to callers beyond this Protocol. Today
    always an Anthropic Files API id; kept as a wrapper rather than a bare
    str so a future extractor can carry a different kind of reference
    (e.g. a set of rasterized page image ids) without changing call sites.
    """

    file_id: str


class DocumentExtractor(Protocol):
    async def upload(self, pdf_bytes: bytes, *, filename: str) -> DocRef: ...

    async def delete(self, ref: DocRef) -> None: ...

    async def extract_toc(self, ref: DocRef, *, page_offset: int = 0) -> TOCResult:
        """``ref`` should already be scoped to a cheap opening excerpt
        (see ``services/ingestion/pdf.slice_pages``) — sending the whole
        document here defeats the point of a cheap TOC pass. ``page_offset``
        is the excerpt's first page minus 1, so returned page numbers land
        back in the original document's numbering.
        """
        ...

    async def extract_section(
        self, ref: DocRef, *, node_id: str, page_offset: int = 0
    ) -> SectionContent:
        """``ref`` should be scoped to just this section's page range."""
        ...
