"""
FastAPI dependency injection — no auth, no user token validation.
user_id is passed as a query/path param or request body field.
"""
from fastapi import Header, HTTPException, Query
from typing import Optional


async def get_user_id(x_user_id: Optional[str] = Header(None)) -> str:
    """
    Reads user identity from the X-User-Id header.
    Auth is removed — this is a placeholder for future re-introduction.
    Falls back to 'default' so dev tooling works without any header.
    """
    return x_user_id or "default"
