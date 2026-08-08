from __future__ import annotations

from bson import ObjectId

from learnai.services.retrieval.vector_store import Chunk, _point_id


def _chunk(**overrides: object) -> Chunk:
    defaults: dict[str, object] = {
        "material_id": ObjectId(),
        "node_id": "1.1",
        "node_path": ["1", "1.1"],
        "chunk_index": 0,
        "page": 3,
        "title": "Limits",
        "text": "text",
    }
    defaults.update(overrides)
    return Chunk(**defaults)  # type: ignore[arg-type]


def test_point_id_is_deterministic() -> None:
    owner = ObjectId()
    chunk = _chunk()

    assert _point_id(owner, chunk) == _point_id(owner, chunk)


def test_point_id_differs_by_chunk_index() -> None:
    owner = ObjectId()
    chunk = _chunk()
    other = _chunk(chunk_index=1)

    assert _point_id(owner, chunk) != _point_id(owner, other)


def test_point_id_differs_by_owner() -> None:
    chunk = _chunk()

    assert _point_id(ObjectId(), chunk) != _point_id(ObjectId(), chunk)
