"""LocalFilesystemStorage: CRUD behavior, and — the part that matters — that
no key can ever resolve to a path outside the storage root.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from learnai.errors import StorageError, ValidationError
from learnai.services.storage.local import LocalFilesystemStorage


@pytest.fixture
def storage(tmp_path: Path) -> LocalFilesystemStorage:
    return LocalFilesystemStorage(tmp_path / "media")


async def test_put_then_get_roundtrips(storage: LocalFilesystemStorage) -> None:
    await storage.put("u1/m1/file.pdf", b"hello world", "application/pdf")
    assert await storage.get("u1/m1/file.pdf") == b"hello world"


async def test_exists_reflects_writes_and_deletes(storage: LocalFilesystemStorage) -> None:
    assert await storage.exists("u1/m1/file.pdf") is False
    await storage.put("u1/m1/file.pdf", b"x", "application/pdf")
    assert await storage.exists("u1/m1/file.pdf") is True
    await storage.delete("u1/m1/file.pdf")
    assert await storage.exists("u1/m1/file.pdf") is False


async def test_delete_of_missing_key_is_not_an_error(storage: LocalFilesystemStorage) -> None:
    await storage.delete("never/existed.pdf")  # must not raise


async def test_get_of_missing_key_raises_storage_error(storage: LocalFilesystemStorage) -> None:
    with pytest.raises(StorageError):
        await storage.get("never/existed.pdf")


async def test_open_streams_content_in_chunks(storage: LocalFilesystemStorage) -> None:
    payload = b"x" * (2 * 1024 * 1024 + 17)  # spans multiple 1 MiB chunks
    await storage.put("big.bin", payload, "application/octet-stream")

    chunks = [chunk async for chunk in storage.open("big.bin")]
    assert b"".join(chunks) == payload
    assert len(chunks) > 1


async def test_put_overwrites_atomically_no_partial_read(storage: LocalFilesystemStorage) -> None:
    await storage.put("f.txt", b"version-one", "text/plain")
    await storage.put("f.txt", b"version-two", "text/plain")
    assert await storage.get("f.txt") == b"version-two"


@pytest.mark.parametrize(
    "malicious_key",
    [
        "../../etc/passwd",
        "../secret.txt",
        "u1/../../etc/passwd",
        "u1/../../../etc/passwd",
        "/etc/passwd",
        "/absolute/path",
        "..",
    ],
)
async def test_path_traversal_is_rejected(
    storage: LocalFilesystemStorage, malicious_key: str
) -> None:
    with pytest.raises((ValidationError, StorageError)):
        await storage.get(malicious_key)
    with pytest.raises((ValidationError, StorageError)):
        await storage.put(malicious_key, b"payload", "text/plain")


async def test_percent_encoded_traversal_is_not_decoded_stays_a_literal_filename(
    storage: LocalFilesystemStorage,
) -> None:
    """We never URL-decode keys, so "%2f" is just three characters in a
    filename, not a slash — this is a safety property worth pinning down
    explicitly, not just "doesn't crash"."""
    key = "u1/..%2f..%2fetc/passwd"
    await storage.put(key, b"payload", "text/plain")
    assert await storage.get(key) == b"payload"
    # And it really did stay nested under the storage root, not escape it.
    assert storage._resolve(key).is_relative_to(storage._root)


async def test_symlink_escape_is_rejected(storage: LocalFilesystemStorage, tmp_path: Path) -> None:
    outside_secret = tmp_path / "outside_secret.txt"
    outside_secret.write_text("top secret")

    # Legitimate-looking key, but the eventual leaf is a symlink pointing
    # outside the storage root — put()/get() must still refuse it.
    root = tmp_path / "media"
    (root / "u1").mkdir(parents=True, exist_ok=True)
    (root / "u1" / "escape.txt").symlink_to(outside_secret)

    with pytest.raises((ValidationError, StorageError)):
        await storage.get("u1/escape.txt")


def test_empty_key_is_rejected(storage: LocalFilesystemStorage) -> None:
    with pytest.raises(ValidationError):
        storage._resolve("")


async def test_root_directory_is_created_on_construction(tmp_path: Path) -> None:
    root = tmp_path / "does" / "not" / "exist" / "yet"
    assert not root.exists()
    LocalFilesystemStorage(root)
    assert root.exists()
