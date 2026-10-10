import asyncio

from fastmcp import Client


def test_mcp_server_exposes_namespaced_tools():
    from mcp_server.server import server

    async def names():
        async with Client(server) as c:
            return {t.name for t in await c.list_tools()}

    tools = asyncio.run(names())
    assert {"books_list_books", "books_get_section_text", "rag_query_knowledge_base",
            "whisper_transcribe_stored_audio", "storage_read_json"} <= tools
    assert "storage_write_json" not in tools
