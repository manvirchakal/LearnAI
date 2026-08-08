"""PyMuPDF utilities — document *manipulation* only, never text extraction.

Text is always read by Claude (see ``services/extraction/``), whether the
source page is scanned, born-digital, a diagram, or handwritten — that's
the whole point of native PDF reading. PyMuPDF's job here is narrower:
counting pages, and slicing a page range into its own standalone PDF
(used both to scope the TOC pass to a cheap opening excerpt, and to slice
a section's page range for the reader UI).
"""

from __future__ import annotations

import io

import pymupdf


def page_count(pdf_bytes: bytes) -> int:
    # pymupdf is a C-extension library with no type stubs — the untyped-call/
    # any-return noise is confined to these two functions.
    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as doc:  # type: ignore[no-untyped-call]
        count: int = doc.page_count
        return count


def slice_pages(pdf_bytes: bytes, *, start_page: int, end_page: int) -> bytes:
    """Extract a 1-indexed, inclusive page range into a new, standalone PDF."""
    with (
        pymupdf.open(stream=pdf_bytes, filetype="pdf") as doc,  # type: ignore[no-untyped-call]
        pymupdf.open() as sliced,  # type: ignore[no-untyped-call]
    ):
        sliced.insert_pdf(doc, from_page=start_page - 1, to_page=end_page - 1)
        buffer = io.BytesIO()
        sliced.save(buffer)
        return buffer.getvalue()
