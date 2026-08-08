"""In-memory ``StorageBackend`` stand-in for tests — no real filesystem or
MinIO, matching the pattern ``tests/fakes/mongo.py`` uses for the database.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from learnai.errors import StorageError


class FakeStorage:
    def __init__(self) -> None:
        self._blobs: dict[str, bytes] = {}

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        self._blobs[key] = data

    async def get(self, key: str) -> bytes:
        try:
            return self._blobs[key]
        except KeyError as exc:
            raise StorageError(f"no such object: {key!r}") from exc

    def open(self, key: str) -> AsyncIterator[bytes]:
        return self._stream(key)

    async def _stream(self, key: str) -> AsyncIterator[bytes]:
        yield await self.get(key)

    async def delete(self, key: str) -> None:
        self._blobs.pop(key, None)

    async def exists(self, key: str) -> bool:
        return key in self._blobs
