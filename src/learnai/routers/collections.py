"""Collections API — CRUD over ``CollectionRepository``, owner-scoped via
``CollectionRepoDep`` (built from the authenticated user in ``deps.py``).

Path/body ids arrive as strings (the JSON-native representation) and are
parsed to ``ObjectId`` here, at the router boundary — the one place that
needs to, since request/response shapes are this layer's job. A malformed
id is a client error (422), not a crash.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter
from pydantic import BaseModel, Field

from learnai.deps import CollectionRepoDep
from learnai.errors import ValidationError
from learnai.repositories.collections import CollectionKind

router = APIRouter(prefix="/api/v1/collections", tags=["collections"])


def _object_id(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except InvalidId as exc:
        raise ValidationError(f"invalid id: {value!r}") from exc


class MaterialRefIn(BaseModel):
    material_id: str
    # Document-tree node_ids (e.g. "1", "1.2" — see schemas.documents.TreeNode),
    # not ObjectIds. Empty means "the whole material" — see
    # services/generation/context.py.
    section_ids: list[str] = Field(default_factory=list)


class MaterialRefOut(BaseModel):
    material_id: str
    section_ids: list[str]
    added_at: datetime | None


class CollectionCreate(BaseModel):
    name: str
    kind: CollectionKind
    parent_collection_id: str | None = None


class CollectionOut(BaseModel):
    id: str
    name: str
    kind: str
    parent_collection_id: str | None
    material_refs: list[MaterialRefOut]
    created_at: datetime
    updated_at: datetime


class UpdateMaterialsRequest(BaseModel):
    material_refs: list[MaterialRefIn]


def _collection_out(doc: dict[str, Any]) -> CollectionOut:
    return CollectionOut(
        id=str(doc["_id"]),
        name=doc["name"],
        kind=doc["kind"],
        parent_collection_id=(
            str(doc["parent_collection_id"]) if doc["parent_collection_id"] else None
        ),
        material_refs=[
            MaterialRefOut(
                material_id=str(ref["material_id"]),
                section_ids=list(ref.get("section_ids", [])),
                added_at=ref.get("added_at"),
            )
            for ref in doc.get("material_refs", [])
        ],
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


@router.post("", response_model=CollectionOut, status_code=201)
async def create_collection(body: CollectionCreate, repo: CollectionRepoDep) -> CollectionOut:
    parent_id = _object_id(body.parent_collection_id) if body.parent_collection_id else None
    collection_id = await repo.create(
        name=body.name, kind=body.kind, parent_collection_id=parent_id
    )
    doc = await repo.get(collection_id)
    return _collection_out(doc)


@router.get("", response_model=list[CollectionOut])
async def list_collections(repo: CollectionRepoDep) -> list[CollectionOut]:
    docs = await repo.list_all()
    return [_collection_out(doc) for doc in docs]


@router.get("/{collection_id}", response_model=CollectionOut)
async def get_collection(collection_id: str, repo: CollectionRepoDep) -> CollectionOut:
    doc = await repo.get(_object_id(collection_id))
    return _collection_out(doc)


@router.put("/{collection_id}/materials", response_model=CollectionOut)
async def update_materials(
    collection_id: str, body: UpdateMaterialsRequest, repo: CollectionRepoDep
) -> CollectionOut:
    now = datetime.now(UTC)
    refs = [
        {
            "material_id": _object_id(ref.material_id),
            "section_ids": list(ref.section_ids),
            "added_at": now,
        }
        for ref in body.material_refs
    ]
    parsed_id = _object_id(collection_id)
    await repo.update_materials(parsed_id, refs)
    doc = await repo.get(parsed_id)
    return _collection_out(doc)
