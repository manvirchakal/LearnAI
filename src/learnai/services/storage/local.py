"""Filesystem-backed storage — the default ``StorageBackend``, rooted at a
directory that's a PVC mount in Kubernetes.

The old ``GET /download-book/{s3_key}`` (``server/main.py:834``) took a raw S3
key straight from the URL. Porting that shape naively to a filesystem turns
it into arbitrary file read — an S3 key like ``../../etc/passwd`` is just a
string to S3, but a real path traversal on disk. ``_resolve`` is the guard:
every key is joined under ``root`` and the resolved path is asserted to
still live inside it before any read, write, or delete. Callers reach this
class only through ``material_id``-keyed routes, never a raw path from a URL.
"""

from __future__ import annotations

import contextlib
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import aiofiles
import aiofiles.os

from learnai.errors import StorageError, ValidationError

_CHUNK_SIZE = 1024 * 1024  # 1 MiB


class LocalFilesystemStorage:
    def __init__(self, root: Path) -> None:
        self._root = root.resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        if not key or key.startswith("/") or ".." in Path(key).parts:
            raise ValidationError(f"invalid storage key: {key!r}")
        candidate = (self._root / key).resolve()
        if not candidate.is_relative_to(self._root):
            raise ValidationError(f"invalid storage key: {key!r}")
        return candidate

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Write to a temp file in the same directory, then atomically rename —
        # a reader never observes a partially-written file.
        tmp_path = path.with_name(f".{path.name}.tmp-{uuid.uuid4().hex[:8]}")
        try:
            async with aiofiles.open(tmp_path, "wb") as f:
                await f.write(data)
            await aiofiles.os.replace(tmp_path, path)
        except OSError as exc:
            if await aiofiles.os.path.exists(tmp_path):
                await aiofiles.os.remove(tmp_path)
            raise StorageError(f"failed to write {key!r}: {exc}") from exc

    async def get(self, key: str) -> bytes:
        path = self._resolve(key)
        try:
            async with aiofiles.open(path, "rb") as f:
                data: bytes = await f.read()
                return data
        except FileNotFoundError as exc:
            raise StorageError(f"no such object: {key!r}") from exc

    def open(self, key: str) -> AsyncIterator[bytes]:
        path = self._resolve(key)
        if not path.exists():
            raise StorageError(f"no such object: {key!r}")
        return self._stream(path)

    async def _stream(self, path: Path) -> AsyncIterator[bytes]:
        async with aiofiles.open(path, "rb") as f:
            while chunk := await f.read(_CHUNK_SIZE):
                yield chunk

    async def delete(self, key: str) -> None:
        path = self._resolve(key)
        # Deleting something already gone is not an error.
        with contextlib.suppress(FileNotFoundError):
            await aiofiles.os.remove(path)

    async def exists(self, key: str) -> bool:
        result: bool = await aiofiles.os.path.exists(self._resolve(key))
        return result
