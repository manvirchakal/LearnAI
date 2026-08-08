"""Blob storage abstraction.

Binaries (PDFs, audio, generated MP3s) never go in Mongo — this Protocol is
where they live. ``LocalFilesystemStorage`` is the default (a PVC mount in
Kubernetes); ``MinIOStorage`` is the escape hatch for clusters with no
ReadWriteMany StorageClass, where the API and worker can't share a
filesystem. Both implement this same interface, so nothing above this layer
knows or cares which one is active.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable


@runtime_checkable
class StorageBackend(Protocol):
    async def put(self, key: str, data: bytes, content_type: str) -> None: ...

    async def get(self, key: str) -> bytes: ...

    def open(self, key: str) -> AsyncIterator[bytes]:
        """Stream large files (PDFs, audio) without buffering the whole thing.

        Not ``async def`` — this is called (not awaited) to get an async
        iterator, then consumed with ``async for chunk in storage.open(key)``.
        """
        ...

    async def delete(self, key: str) -> None: ...

    async def exists(self, key: str) -> bool: ...
