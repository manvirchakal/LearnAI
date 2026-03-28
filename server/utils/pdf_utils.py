"""
PyMuPDF (fitz) helpers — replaces AWS Textract for PDF text extraction.
"""
import io
import logging
from pathlib import Path
from typing import List, Tuple

import fitz  # PyMuPDF
from PIL import Image

logger = logging.getLogger(__name__)


def extract_text_from_pages(pdf_path: str | Path, start_page: int, end_page: int) -> str:
    """Extract plain text from a page range (1-indexed)."""
    text_parts = []
    with fitz.open(str(pdf_path)) as doc:
        total = len(doc)
        for page_num in range(start_page - 1, min(end_page, total)):
            page = doc[page_num]
            text_parts.append(f"Page {page_num + 1}:\n{page.get_text()}\n")
    return "\n".join(text_parts)


def extract_toc(pdf_path: str | Path) -> List[dict]:
    """
    Extract built-in table of contents using PyMuPDF.
    Returns list of [level, title, page] entries.
    Falls back to empty list if no TOC is embedded.
    """
    with fitz.open(str(pdf_path)) as doc:
        toc = doc.get_toc()   # [[level, title, page], ...]
    return [{"level": t[0], "title": t[1], "page": t[2]} for t in toc]


def extract_section_pdf(
    pdf_path: str | Path, start_page: int, end_page: int
) -> bytes:
    """Return a new PDF containing only pages [start_page, end_page] (1-indexed)."""
    src = fitz.open(str(pdf_path))
    out = fitz.open()
    total = len(src)
    out.insert_pdf(src, from_page=start_page - 1, to_page=min(end_page, total) - 1)
    buf = io.BytesIO()
    out.save(buf)
    return buf.getvalue()


def pages_to_images(
    pdf_path: str | Path, start_page: int, end_page: int, size: int = 1152
) -> List[bytes]:
    """
    Render PDF pages as JPEG images (square, white-background).
    Replaces prepare_toc_images from the old monolith.
    """
    images = []
    with fitz.open(str(pdf_path)) as doc:
        total = len(doc)
        for page_num in range(start_page - 1, min(end_page, total)):
            page = doc[page_num]
            pix = page.get_pixmap()
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # Resize maintaining aspect ratio onto white square background
            aspect = img.width / img.height
            if aspect > 1:
                new_w, new_h = size, int(size / aspect)
            else:
                new_w, new_h = int(size * aspect), size
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

            background = Image.new("RGB", (size, size), (255, 255, 255))
            background.paste(img, ((size - new_w) // 2, (size - new_h) // 2))

            buf = io.BytesIO()
            background.save(buf, format="JPEG")
            images.append(buf.getvalue())
    return images


def extract_text_and_tables_pymupdf(pdf_path: str | Path, start_page: int, end_page: int) -> str:
    """
    Replaces extract_text_and_tables (Textract).
    Uses PyMuPDF text blocks for text + basic table detection.
    """
    parts = []
    with fitz.open(str(pdf_path)) as doc:
        total = len(doc)
        for page_num in range(start_page - 1, min(end_page, total)):
            page = doc[page_num]
            parts.append(f"Page {page_num + 1}:\n{page.get_text()}\n")
    return "\n".join(parts)
