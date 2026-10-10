"""MCP tools: browse uploaded books and read section text (PyMuPDF, local)."""
from fastmcp import FastMCP

from services import book_service

mcp = FastMCP("books")


@mcp.tool()
def list_books(user_id: str = "default") -> list:
    """List a user's uploaded books (file_id, title, page and section counts)."""
    return book_service.list_books(user_id)


@mcp.tool()
def get_book_structure(file_id: str, user_id: str = "default") -> dict:
    """Chapters and sections of a book, with stable section ids and page ranges."""
    return book_service.get_book(user_id, file_id)


@mcp.tool()
def get_section_text(file_id: str, section_id: str, user_id: str = "default") -> str:
    """Extracted text of one section (cached and embedded for RAG on first read)."""
    return book_service.get_section_text(user_id, file_id, section_id)
