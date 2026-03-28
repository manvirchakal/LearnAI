"""MCP tool: PDF text and TOC extraction via PyMuPDF."""
from fastmcp import FastMCP
from utils.pdf_utils import extract_text_from_pages, extract_toc, extract_text_and_tables_pymupdf

mcp = FastMCP("pdf")


@mcp.tool()
def extract_text(pdf_path: str, start_page: int, end_page: int) -> str:
    """Extract plain text from a PDF page range."""
    return extract_text_from_pages(pdf_path, start_page, end_page)


@mcp.tool()
def get_toc(pdf_path: str) -> list:
    """Extract the built-in table of contents from a PDF."""
    return extract_toc(pdf_path)


@mcp.tool()
def extract_section_text(pdf_path: str, start_page: int, end_page: int) -> str:
    """Extract text and tables from a PDF section using PyMuPDF."""
    return extract_text_and_tables_pymupdf(pdf_path, start_page, end_page)
