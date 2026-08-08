"""Anthropic implementation of ``DocumentExtractor``: native PDF ``document``
content blocks plus the Files API for upload.

Two mechanics, one per task, deliberately not mixed — citations and
``output_config.format`` are mutually exclusive (a 400 if combined):

* **TOC pass** — ``output_config.format``: pure structure, no provenance
  needed.
* **Section extraction** — ``citations: {enabled: true}`` on the document
  block, with a plain-text instruction to transcribe verbatim. Citations
  segment Claude's own response into text blocks as it quotes the source,
  each carrying a ``page_location`` — that's what gives real page
  provenance, and it only happens on ordinary text output, not inside a
  forced tool call's structured input. (An earlier draft of this forced a
  tool call for section extraction; that suppresses the very citation-
  bearing text blocks the citations feature relies on, so it doesn't work.)
"""

from __future__ import annotations

import anthropic
import structlog

from learnai.config import LLMTask, Settings
from learnai.errors import UpstreamError
from learnai.schemas.documents import Citation, SectionContent, TOCResult, TreeNode
from learnai.services.extraction.base import DocRef

logger = structlog.get_logger(__name__)

_TOC_INSTRUCTION = (
    "Extract the full hierarchical table of contents from this document. "
    "For each entry, give a stable node_id ('1', '1.2', '1.2.3' — matching "
    "outline depth), a title, and the start_page/end_page it spans (page "
    "numbers as printed in this excerpt). Nest subsections under their "
    "parent. If no clear table of contents exists, infer chapter/section "
    "boundaries from headings visible in the document itself."
)

_SECTION_INSTRUCTION = (
    "Transcribe the full text of this document verbatim, in reading order, "
    "preserving paragraph structure. Do not summarize, paraphrase, or omit "
    "anything."
)


def _shift_pages(nodes: list[TreeNode], offset: int) -> None:
    for node in nodes:
        node.start_page += offset
        node.end_page += offset
        _shift_pages(node.nodes, offset)


class AnthropicPDFExtractor:
    def __init__(self, client: anthropic.AsyncAnthropic, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    async def upload(self, pdf_bytes: bytes, *, filename: str) -> DocRef:
        try:
            uploaded = await self._client.beta.files.upload(
                file=(filename, pdf_bytes, "application/pdf")
            )
        except anthropic.APIStatusError as exc:
            raise UpstreamError(f"failed to upload {filename} to Anthropic Files API") from exc
        return DocRef(file_id=uploaded.id)

    async def delete(self, ref: DocRef) -> None:
        try:
            await self._client.beta.files.delete(ref.file_id)
        except anthropic.APIStatusError:
            # Best-effort cleanup of a short-lived excerpt upload — a failed
            # delete leaves an orphaned file (within the 100GB org cap), not
            # a broken ingestion, so it's logged rather than raised.
            logger.warning("anthropic_file_delete_failed", file_id=ref.file_id)

    async def extract_toc(self, ref: DocRef, *, page_offset: int = 0) -> TOCResult:
        try:
            # The dynamically-built content-block dicts don't structurally
            # match the SDK's precise TypedDict union; the shape is correct
            # (validated at runtime by the API itself), so silence the
            # overload mismatch here rather than fight it.
            message = await self._client.beta.messages.create(  # type: ignore[call-overload]
                model=self._settings.model_for(LLMTask.toc),
                max_tokens=self._settings.max_tokens_for(LLMTask.toc),
                betas=["files-api-2025-04-14"],
                output_config={
                    "effort": self._settings.effort_for(LLMTask.toc),
                    "format": {"type": "json_schema", "schema": TOCResult.model_json_schema()},
                },
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "document",
                                "source": {"type": "file", "file_id": ref.file_id},
                            },
                            {"type": "text", "text": _TOC_INSTRUCTION},
                        ],
                    }
                ],
            )
        except anthropic.APIStatusError as exc:
            raise UpstreamError("Anthropic TOC extraction request failed") from exc

        if message.stop_reason == "refusal":
            raise UpstreamError("Anthropic declined the TOC extraction request")

        text = next((block.text for block in message.content if block.type == "text"), None)
        if text is None:
            raise UpstreamError("Anthropic TOC response contained no text block")

        try:
            result = TOCResult.model_validate_json(text)
        except ValueError as exc:
            raise UpstreamError("Anthropic returned an invalid TOC structure") from exc

        if page_offset:
            _shift_pages(result.tree, page_offset)
        return result

    async def extract_section(
        self, ref: DocRef, *, node_id: str, page_offset: int = 0
    ) -> SectionContent:
        try:
            message = await self._client.beta.messages.create(
                model=self._settings.model_for(LLMTask.section_extraction),
                max_tokens=self._settings.max_tokens_for(LLMTask.section_extraction),
                betas=["files-api-2025-04-14"],
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "document",
                                "source": {"type": "file", "file_id": ref.file_id},
                                "citations": {"enabled": True},
                            },
                            {"type": "text", "text": _SECTION_INSTRUCTION},
                        ],
                    }
                ],
            )
        except anthropic.APIStatusError as exc:
            raise UpstreamError(
                f"Anthropic section extraction request failed for {node_id}"
            ) from exc

        if message.stop_reason == "refusal":
            raise UpstreamError(f"Anthropic declined section extraction for {node_id}")

        text_blocks = [block for block in message.content if block.type == "text"]
        if not text_blocks:
            raise UpstreamError(f"Anthropic response for section {node_id} contained no text block")

        full_text = "".join(block.text for block in text_blocks)
        citations = [
            Citation(
                cited_text=citation.cited_text,
                start_page=citation.start_page_number + page_offset,
                end_page=citation.end_page_number + page_offset,
            )
            for block in text_blocks
            for citation in (block.citations or [])
            if citation.type == "page_location"
        ]
        return SectionContent(node_id=node_id, text=full_text, citations=citations)
