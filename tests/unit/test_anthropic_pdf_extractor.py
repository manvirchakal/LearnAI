from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import anthropic
import httpx
import pytest

from learnai.config import Settings
from learnai.errors import UpstreamError
from learnai.services.extraction.anthropic_pdf import AnthropicPDFExtractor
from learnai.services.extraction.base import DocRef


@pytest.fixture
def settings() -> Settings:
    return Settings(
        anthropic_api_key="sk-test",
        google_client_id="test-client-id",
        session_secret="a-test-secret-at-least-32-bytes-long",
    )


def _toc_message(json_text: str, *, stop_reason: str = "end_turn") -> SimpleNamespace:
    return SimpleNamespace(
        stop_reason=stop_reason, content=[SimpleNamespace(type="text", text=json_text)]
    )


def _citation(start: int, end: int, text: str = "quoted text") -> SimpleNamespace:
    return SimpleNamespace(
        type="page_location", cited_text=text, start_page_number=start, end_page_number=end
    )


def _section_message(
    text_blocks: list[tuple[str, list[SimpleNamespace] | None]], *, stop_reason: str = "end_turn"
) -> SimpleNamespace:
    content = [
        SimpleNamespace(type="text", text=text, citations=citations)
        for text, citations in text_blocks
    ]
    return SimpleNamespace(stop_reason=stop_reason, content=content)


def _fake_sdk_client(create_result: object) -> MagicMock:
    fake = MagicMock()
    fake.beta.messages.create = AsyncMock(return_value=create_result)
    fake.beta.files.upload = AsyncMock(return_value=SimpleNamespace(id="file_abc123"))
    fake.beta.files.delete = AsyncMock(return_value=None)
    return fake


async def test_upload_returns_doc_ref(settings: Settings) -> None:
    fake = _fake_sdk_client(create_result=None)
    extractor = AnthropicPDFExtractor(fake, settings)

    ref = await extractor.upload(b"%PDF-1.4 fake bytes", filename="book.pdf")

    assert ref == DocRef(file_id="file_abc123")
    fake.beta.files.upload.assert_awaited_once()


async def test_delete_swallows_api_errors(settings: Settings) -> None:
    fake = _fake_sdk_client(create_result=None)
    request = httpx.Request("DELETE", "https://api.anthropic.com/v1/files/file_abc123")
    response = httpx.Response(status_code=404, request=request)
    fake.beta.files.delete = AsyncMock(
        side_effect=anthropic.APIStatusError("not found", response=response, body=None)
    )
    extractor = AnthropicPDFExtractor(fake, settings)

    await extractor.delete(DocRef(file_id="file_abc123"))  # must not raise


async def test_extract_toc_parses_structured_result(settings: Settings) -> None:
    json_text = (
        '{"tree": [{"node_id": "1", "title": "Chapter 1", "start_page": 1, '
        '"end_page": 10, "summary": null, "nodes": []}], '
        '"confidence": "high", "notes": null}'
    )
    fake = _fake_sdk_client(_toc_message(json_text))
    extractor = AnthropicPDFExtractor(fake, settings)

    result = await extractor.extract_toc(DocRef(file_id="file_abc123"))

    assert result.confidence == "high"
    assert result.tree[0].title == "Chapter 1"
    assert result.tree[0].start_page == 1


async def test_extract_toc_applies_page_offset(settings: Settings) -> None:
    json_text = (
        '{"tree": [{"node_id": "1", "title": "Chapter 1", "start_page": 1, '
        '"end_page": 10, "summary": null, "nodes": [{"node_id": "1.1", '
        '"title": "1.1", "start_page": 2, "end_page": 5, "summary": null, "nodes": []}]}], '
        '"confidence": "high", "notes": null}'
    )
    fake = _fake_sdk_client(_toc_message(json_text))
    extractor = AnthropicPDFExtractor(fake, settings)

    result = await extractor.extract_toc(DocRef(file_id="file_abc123"), page_offset=100)

    assert result.tree[0].start_page == 101
    assert result.tree[0].end_page == 110
    assert result.tree[0].nodes[0].start_page == 102


async def test_extract_toc_raises_on_refusal(settings: Settings) -> None:
    fake = _fake_sdk_client(_toc_message("", stop_reason="refusal"))
    extractor = AnthropicPDFExtractor(fake, settings)

    with pytest.raises(UpstreamError, match="declined"):
        await extractor.extract_toc(DocRef(file_id="file_abc123"))


async def test_extract_toc_raises_on_invalid_json(settings: Settings) -> None:
    fake = _fake_sdk_client(_toc_message("not valid json"))
    extractor = AnthropicPDFExtractor(fake, settings)

    with pytest.raises(UpstreamError, match="invalid TOC structure"):
        await extractor.extract_toc(DocRef(file_id="file_abc123"))


async def test_extract_section_concatenates_text_and_collects_citations(settings: Settings) -> None:
    message = _section_message(
        [
            ("First paragraph. ", [_citation(1, 1, "First paragraph.")]),
            ("Second paragraph.", [_citation(2, 2, "Second paragraph.")]),
        ]
    )
    fake = _fake_sdk_client(message)
    extractor = AnthropicPDFExtractor(fake, settings)

    section = await extractor.extract_section(DocRef(file_id="file_abc123"), node_id="1.1")

    assert section.text == "First paragraph. Second paragraph."
    assert section.node_id == "1.1"
    assert [c.start_page for c in section.citations] == [1, 2]


async def test_extract_section_applies_page_offset_to_citations(settings: Settings) -> None:
    message = _section_message([("Some text.", [_citation(1, 2)])])
    fake = _fake_sdk_client(message)
    extractor = AnthropicPDFExtractor(fake, settings)

    section = await extractor.extract_section(
        DocRef(file_id="file_abc123"), node_id="1.1", page_offset=50
    )

    assert section.citations[0].start_page == 51
    assert section.citations[0].end_page == 52


async def test_extract_section_ignores_non_page_location_citations(settings: Settings) -> None:
    char_citation = SimpleNamespace(type="char_location", cited_text="x")
    message = _section_message([("Some text.", [char_citation])])
    fake = _fake_sdk_client(message)
    extractor = AnthropicPDFExtractor(fake, settings)

    section = await extractor.extract_section(DocRef(file_id="file_abc123"), node_id="1.1")

    assert section.citations == []


async def test_extract_section_raises_on_refusal(settings: Settings) -> None:
    fake = _fake_sdk_client(_section_message([], stop_reason="refusal"))
    extractor = AnthropicPDFExtractor(fake, settings)

    with pytest.raises(UpstreamError, match="declined"):
        await extractor.extract_section(DocRef(file_id="file_abc123"), node_id="1.1")


async def test_extract_section_raises_when_no_text_blocks(settings: Settings) -> None:
    fake = _fake_sdk_client(_section_message([]))
    extractor = AnthropicPDFExtractor(fake, settings)

    with pytest.raises(UpstreamError, match="no text block"):
        await extractor.extract_section(DocRef(file_id="file_abc123"), node_id="1.1")
