"""MCP tool: local file storage (read/write)."""
from fastmcp import FastMCP
from core import storage

mcp = FastMCP("storage")


@mcp.tool()
def read_json(key: str) -> dict:
    """Read a JSON object from local storage by key."""
    return storage.load_json(key)


@mcp.tool()
def write_json(key: str, data: dict) -> str:
    """Write a JSON object to local storage."""
    storage.save_json(key, data)
    return f"Saved to {key}"


@mcp.tool()
def read_text(key: str) -> str:
    """Read a text file from local storage."""
    return storage.load_text(key)


@mcp.tool()
def list_keys(prefix: str) -> list:
    """List all storage keys under a given prefix."""
    return storage.list_keys(prefix)
