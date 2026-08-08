"""Live contract test for ``AnthropicPDFExtractor`` — the actual
verification that native PDF ``document`` blocks, the Files API upload,
and ``output_config.format``-constrained TOC extraction work together
against the real Anthropic API. The unit tests in
``tests/unit/test_anthropic_pdf_extractor.py`` cover request/response
handling against a mocked SDK client; this hits the real thing.

Marked ``live`` (see pyproject.toml) and deselected by default. Skips
itself when no real credential is configured, so a bare ``pytest -m live``
run degrades to "skipped" rather than "failed" in an environment with no
Anthropic access. Run explicitly:

    ANTHROPIC_API_KEY=... pytest -m live tests/contract/test_pdf_extraction_live.py
"""

from __future__ import annotations

import os

import anthropic
import pymupdf
import pytest

from learnai.config import Settings
from learnai.services.extraction.anthropic_pdf import AnthropicPDFExtractor

pytestmark = pytest.mark.live

# See tests/contract/test_llm_adapters_live.py — the same conftest.py
# placeholder this compares against, to skip rather than fail with a fake key.
_PLACEHOLDER_ANTHROPIC_KEY = "test-key-not-real"


def _make_pdf() -> bytes:
    doc = pymupdf.open()  # type: ignore[no-untyped-call]
    page = doc.new_page()
    page.insert_text((72, 72), "Table of Contents")
    page.insert_text((72, 100), "Chapter 1: Limits ... 1")
    page.insert_text((72, 120), "Chapter 2: Derivatives ... 20")
    buffer: bytes = doc.tobytes()  # type: ignore[no-untyped-call]
    doc.close()  # type: ignore[no-untyped-call]
    return buffer


@pytest.mark.skipif(
    os.environ.get("ANTHROPIC_API_KEY", "") in ("", _PLACEHOLDER_ANTHROPIC_KEY),
    reason="no real ANTHROPIC_API_KEY set",
)
async def test_upload_extract_toc_and_delete_round_trip() -> None:
    settings = Settings(
        google_client_id="live-test", session_secret="a-test-secret-at-least-32-bytes-long"
    )
    extractor = AnthropicPDFExtractor(anthropic.AsyncAnthropic(), settings)

    ref = await extractor.upload(_make_pdf(), filename="toc-fixture.pdf")
    try:
        result = await extractor.extract_toc(ref)
    finally:
        await extractor.delete(ref)

    assert result.confidence in ("high", "medium", "low")
    assert len(result.tree) >= 1
    assert all(node.node_id for node in result.tree)
