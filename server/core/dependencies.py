"""
FastAPI dependencies. There is no auth yet: identity is the X-User-Id header,
defaulting to "default" so local single-user use needs no setup.
"""
import re
from typing import Optional

from fastapi import Header, HTTPException

# user ids become storage path segments and Chroma collection names
_USER_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


async def get_user_id(x_user_id: Optional[str] = Header(None)) -> str:
    user_id = x_user_id or "default"
    if not _USER_ID.match(user_id):
        raise HTTPException(status_code=400, detail="X-User-Id must be 1-64 chars of [A-Za-z0-9_-]")
    return user_id
