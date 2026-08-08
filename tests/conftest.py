"""Session-wide test environment.

Sets required env vars *before* anything imports ``learnai.config`` —
``get_settings()`` is ``@lru_cache``d, so whichever env is in place the first
time any test module (in any collection order) triggers that first call is
what every test gets for the rest of the session. A top-level conftest is
loaded before test-module collection, which is what makes this reliable
regardless of import order.

In particular: ``STORAGE_ROOT`` defaults to ``/data/media`` in production
(a PVC mount inside the container) — the right default for the Docker
image, but not necessarily writable by whatever user runs the test suite
directly (a local dev machine, a CI runner). Tests get an isolated tmp
directory instead, cleaned up at session end.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Iterator

import pytest

_TEST_STORAGE_ROOT = tempfile.mkdtemp(prefix="learnai-test-media-")

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")
os.environ.setdefault("SESSION_SECRET", "test-only-secret-not-for-production-32chars")
os.environ.setdefault("STORAGE_ROOT", _TEST_STORAGE_ROOT)


@pytest.fixture(scope="session", autouse=True)
def _cleanup_test_storage_root() -> Iterator[None]:
    yield
    shutil.rmtree(_TEST_STORAGE_ROOT, ignore_errors=True)
