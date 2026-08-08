from __future__ import annotations

import pymupdf

from learnai.services.ingestion.pdf import page_count, slice_pages


def _make_pdf(num_pages: int) -> bytes:
    # pymupdf is a C-extension library with no type stubs.
    doc = pymupdf.open()  # type: ignore[no-untyped-call]
    for i in range(num_pages):
        page = doc.new_page()
        page.insert_text((72, 72), f"Page {i + 1}")
    buffer: bytes = doc.tobytes()  # type: ignore[no-untyped-call]
    doc.close()  # type: ignore[no-untyped-call]
    return buffer


def test_page_count_matches_document() -> None:
    assert page_count(_make_pdf(5)) == 5


def test_slice_pages_returns_only_requested_range() -> None:
    pdf_bytes = _make_pdf(10)

    sliced = slice_pages(pdf_bytes, start_page=3, end_page=5)

    assert page_count(sliced) == 3
    with pymupdf.open(stream=sliced, filetype="pdf") as doc:  # type: ignore[no-untyped-call]
        first_page_text = doc[0].get_text()
    assert "Page 3" in first_page_text


def test_slice_pages_single_page() -> None:
    pdf_bytes = _make_pdf(3)

    sliced = slice_pages(pdf_bytes, start_page=1, end_page=1)

    assert page_count(sliced) == 1
