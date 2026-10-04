"""
FastMCP server — registers all LearnAI MCP tools.
Can be run standalone: python -m mcp_server.server
or imported for embedding.
"""
from fastmcp import FastMCP

from mcp_server.tools.storage_tool import mcp as storage_mcp
from mcp_server.tools.pdf_tool import mcp as pdf_mcp
from mcp_server.tools.rag_tool import mcp as rag_mcp
from mcp_server.tools.whisper_tool import mcp as whisper_mcp
from mcp_server.tools.translate_tool import mcp as translate_mcp
from mcp_server.tools.tts_tool import mcp as tts_mcp

server = FastMCP("learnai")
server.mount(storage_mcp, namespace="storage")
server.mount(pdf_mcp, namespace="pdf")
server.mount(rag_mcp, namespace="rag")
server.mount(whisper_mcp, namespace="whisper")
server.mount(translate_mcp, namespace="translate")
server.mount(tts_mcp, namespace="tts")


if __name__ == "__main__":
    server.run()
