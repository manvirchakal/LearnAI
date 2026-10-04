"""MCP tool: local ChromaDB vector store query and ingestion."""
from fastmcp import FastMCP
from services.rag_service import retrieve_context, ingest_section

mcp = FastMCP("rag")


@mcp.tool()
def query_knowledge_base(user_id: str, query: str, top_k: int = 3, file_id: str = "") -> str:
    """Retrieve relevant context from the user's local vector store."""
    return retrieve_context(user_id, query, top_k=top_k, file_id=file_id or None)


@mcp.tool()
def ingest_text(user_id: str, file_id: str, section_name: str, text: str) -> str:
    """Ingest a text chunk into the user's ChromaDB collection."""
    ingest_section(user_id, file_id, section_name, text)
    return f"Ingested {section_name} for {user_id}/{file_id}"
