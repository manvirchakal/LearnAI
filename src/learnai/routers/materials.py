"""Materials API — PDF upload (kicks off async TOC extraction), status,
document tree, and lazy per-section reads.

Upload returns ``202`` with a ``poll_url`` rather than blocking on
extraction — the old ``server/main.py`` blocked request handlers on
``time.sleep`` and long open-connection polling loops for exactly this kind
of work (see the modernization plan's "Long-running jobs" section); any
load balancer with a modest idle timeout killed those. The client polls
``GET /api/v1/jobs/{job_id}`` instead.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel

from learnai.deps import (
    ArqPoolDep,
    CurrentUser,
    EmbedderDep,
    ExtractorDep,
    JobRepoDep,
    MaterialRepoDep,
    SectionRepoDep,
    SettingsDep,
    StorageDep,
    VectorStoreDep,
)
from learnai.errors import Conflict, ValidationError
from learnai.repositories.materials import MaterialStatus
from learnai.schemas.documents import SectionContent, TOCResult
from learnai.services.ingestion.pipeline import get_or_extract_section

router = APIRouter(prefix="/api/v1/materials", tags=["materials"])

_MAX_UPLOAD_BYTES = 32 * 1024 * 1024  # Anthropic's own per-request document limit


def _object_id(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except InvalidId as exc:
        raise ValidationError(f"invalid id: {value!r}") from exc


class MaterialOut(BaseModel):
    id: str
    filename: str
    content_type: str
    size_bytes: int
    status: MaterialStatus
    page_count: int | None
    error: str | None
    created_at: datetime
    updated_at: datetime


class UploadAccepted(BaseModel):
    material_id: str
    job_id: str
    poll_url: str


def _material_out(doc: dict[str, Any]) -> MaterialOut:
    return MaterialOut(
        id=str(doc["_id"]),
        filename=doc["filename"],
        content_type=doc["content_type"],
        size_bytes=doc["size_bytes"],
        status=doc["status"],
        page_count=doc["page_count"],
        error=doc["error"],
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


@router.post("", response_model=UploadAccepted, status_code=202)
async def upload_material(
    user: CurrentUser,
    materials: MaterialRepoDep,
    jobs: JobRepoDep,
    storage: StorageDep,
    arq_pool: ArqPoolDep,
    file: UploadFile = File(...),
) -> UploadAccepted:
    if file.content_type != "application/pdf":
        raise ValidationError(f"unsupported content type: {file.content_type!r}")
    data = await file.read()
    if not data:
        raise ValidationError("uploaded file is empty")
    if len(data) > _MAX_UPLOAD_BYTES:
        raise ValidationError(f"file exceeds the {_MAX_UPLOAD_BYTES} byte upload limit")

    storage_key = f"materials/{user['_id']}/{uuid.uuid4().hex}.pdf"
    await storage.put(storage_key, data, "application/pdf")

    material_id = await materials.create(
        filename=file.filename or "upload.pdf",
        content_type=file.content_type,
        storage_key=storage_key,
        size_bytes=len(data),
    )
    job_id = await jobs.create(kind="toc_extraction", payload={"material_id": str(material_id)})
    await arq_pool.enqueue_job(
        "extract_toc_task",
        owner_id=str(user["_id"]),
        material_id=str(material_id),
        job_id=str(job_id),
    )

    return UploadAccepted(
        material_id=str(material_id),
        job_id=str(job_id),
        poll_url=f"/api/v1/jobs/{job_id}",
    )


@router.get("", response_model=list[MaterialOut])
async def list_materials(materials: MaterialRepoDep) -> list[MaterialOut]:
    docs = await materials.list_all()
    return [_material_out(doc) for doc in docs]


@router.get("/{material_id}", response_model=MaterialOut)
async def get_material(material_id: str, materials: MaterialRepoDep) -> MaterialOut:
    doc = await materials.get(_object_id(material_id))
    return _material_out(doc)


@router.get("/{material_id}/tree", response_model=TOCResult)
async def get_material_tree(material_id: str, materials: MaterialRepoDep) -> TOCResult:
    doc = await materials.get(_object_id(material_id))
    if doc["tree"] is None:
        raise Conflict(f"material {material_id} has no ready document tree yet")
    return TOCResult.model_validate(doc["tree"])


@router.get("/{material_id}/sections/{node_id}", response_model=SectionContent)
async def get_section(
    material_id: str,
    node_id: str,
    user: CurrentUser,
    materials: MaterialRepoDep,
    sections: SectionRepoDep,
    storage: StorageDep,
    extractor: ExtractorDep,
    embedder: EmbedderDep,
    vector_store: VectorStoreDep,
    settings: SettingsDep,
) -> SectionContent:
    return await get_or_extract_section(
        materials=materials,
        sections=sections,
        storage=storage,
        extractor=extractor,
        embedder=embedder,
        vector_store=vector_store,
        settings=settings,
        owner_id=user["_id"],
        material_id=_object_id(material_id),
        node_id=node_id,
    )
