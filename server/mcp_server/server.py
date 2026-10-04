"""
FastMCP server — registers all LearnAI MCP tools.
Can be run standalone: python -m mcp.server
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
server.mount("storage", storage_mcp)
server.mount("pdf", pdf_mcp)
server.mount("rag", rag_mcp)
server.mount("whisper", whisper_mcp)
server.mount("translate", translate_mcp)
server.mount("tts", tts_mcp)


if __name__ == "__main__":
    server.run()
