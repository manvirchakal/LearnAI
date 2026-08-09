"""Content fingerprint for artifact caching — regenerating with the same
inputs is a cache hit (``ArtifactRepository``), not a fresh, paid LLM
call. Changing any input (the collection's material content, the
learning profile description, ...) changes the fingerprint.
"""

from __future__ import annotations

import hashlib


def fingerprint(**parts: str) -> str:
    joined = "\x1f".join(f"{key}={value}" for key, value in sorted(parts.items()))
    return hashlib.sha256(joined.encode()).hexdigest()
