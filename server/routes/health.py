"""
Health API.

    GET /health               liveness: the process is serving
    GET /health/ready         readiness: storage is writable
    GET /health/dependencies  reachability of the model servers (LLM, embeddings, STT)

Readiness deliberately ignores the model servers: if the GPU host is down the
pod should keep serving the library, PDFs and cached study materials.
"""
import uuid

import httpx
from fastapi import APIRouter, HTTPException

from core.config import settings

router = APIRouter(prefix="/health", tags=["meta"])


@router.get("")
def health():
    return {"status": "ok"}


@router.get("/ready")
def ready():
    probe = settings.DATA_DIR / f".ready-{uuid.uuid4().hex}"
    try:
        probe.write_text("ok")
        probe.unlink()
    except OSError as e:
        raise HTTPException(status_code=503, detail=f"DATA_DIR not writable: {e}")
    return {"status": "ready"}


def _probe_openai(base_url: str, model: str) -> dict:
    try:
        r = httpx.get(f"{base_url.rstrip('/')}/models", timeout=5,
                      headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"})
        r.raise_for_status()
        served = [m["id"] for m in r.json().get("data", [])]
    except Exception as e:
        return {"ok": False, "url": base_url, "error": str(e)}
    ok = not model or model in served
    return {"ok": ok, "url": base_url, "model": model or None, "served": served,
            **({} if ok else {"error": f"{model} is not served here"})}


@router.get("/dependencies")
def dependencies():
    deps: dict = {}
    if settings.LLM_PROVIDER == "openai":
        deps["llm"] = _probe_openai(settings.OPENAI_BASE_URL, settings.LLM_MODEL)
        if settings.LLM_VISION_ENABLED and settings.LLM_VISION_MODEL:
            deps["vision"] = _probe_openai(settings.OPENAI_BASE_URL, settings.LLM_VISION_MODEL)
    else:
        deps["llm"] = {"ok": True, "provider": "bedrock", "note": "not probed"}
    deps["embeddings"] = (_probe_openai(settings.embedding_base_url, settings.EMBEDDING_MODEL)
                          if settings.EMBEDDING_PROVIDER == "openai" else {"ok": True, "provider": "local"})
    deps["stt"] = (_probe_openai(settings.stt_base_url, settings.STT_MODEL)
                   if settings.STT_PROVIDER == "openai" else {"ok": True, "provider": "local"})
    return {"ok": all(d["ok"] for d in deps.values()), **deps}
