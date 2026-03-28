"""
Local filesystem storage abstraction — replaces all AWS S3 operations.
Mirrors the S3 key-path schema exactly so the rest of the codebase uses
the same path strings (e.g. "learning_profiles/{user_id}.json").
"""
import json
import logging
import shutil
from pathlib import Path
from typing import Any, List, Optional

from core.config import settings

logger = logging.getLogger(__name__)


def _resolve(key: str) -> Path:
    """Turn an S3-style key into an absolute local path under DATA_DIR."""
    return settings.DATA_DIR / key


# ── JSON helpers ──────────────────────────────────────────────────────────────

def save_json(key: str, data: Any) -> None:
    path = _resolve(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def load_json(key: str) -> Any:
    path = _resolve(key)
    if not path.exists():
        raise FileNotFoundError(f"Storage key not found: {key}")
    return json.loads(path.read_text(encoding="utf-8"))


def json_exists(key: str) -> bool:
    return _resolve(key).exists()


# ── Binary (file) helpers ─────────────────────────────────────────────────────

def save_bytes(key: str, data: bytes) -> None:
    path = _resolve(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def load_bytes(key: str) -> bytes:
    path = _resolve(key)
    if not path.exists():
        raise FileNotFoundError(f"Storage key not found: {key}")
    return path.read_bytes()


def load_text(key: str) -> str:
    path = _resolve(key)
    if not path.exists():
        raise FileNotFoundError(f"Storage key not found: {key}")
    return path.read_text(encoding="utf-8")


def save_text(key: str, text: str) -> None:
    path = _resolve(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def save_file(key: str, source_path: str | Path) -> None:
    dest = _resolve(key)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(source_path), str(dest))


def get_local_path(key: str) -> Path:
    """Return the local Path for a key (creates parent dirs)."""
    path = _resolve(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


# ── Listing ───────────────────────────────────────────────────────────────────

def list_keys(prefix: str) -> List[str]:
    """List all keys (relative to DATA_DIR) under a given prefix."""
    base = _resolve(prefix)
    if not base.exists():
        return []
    return [
        str(p.relative_to(settings.DATA_DIR))
        for p in sorted(base.rglob("*"))
        if p.is_file()
    ]


def list_json_keys(prefix: str) -> List[str]:
    return [k for k in list_keys(prefix) if k.endswith(".json")]


# ── Delete ────────────────────────────────────────────────────────────────────

def delete(key: str) -> None:
    path = _resolve(key)
    if path.exists():
        path.unlink()


def delete_prefix(prefix: str) -> None:
    base = _resolve(prefix)
    if base.exists():
        shutil.rmtree(str(base))
