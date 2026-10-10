"""
Background tasks — long jobs (YouTube transcription) run on a worker thread
while the client polls GET /media/tasks/{task_id} for their progress:

    {"task_id", "kind", "status": "queued" | "running" | "done" | "failed",
     "stage", "progress": 0-1 or null, "title", "result", "error"}

Tasks are kept in memory: the server runs one worker process (see Dockerfile),
and a task lost to a restart is simply not found. Finished tasks are dropped
TASK_TTL_SECONDS after they finish.
"""
import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

MAX_RUNNING = 2  # more wait as "queued"; transcription is CPU/GPU-heavy
TASK_TTL_SECONDS = 3600

Report = Callable[..., None]  # report(stage=..., progress=..., title=...)

_tasks: Dict[str, Tuple[str, dict]] = {}  # task_id -> (user_id, task)
_lock = threading.Lock()
_pool = ThreadPoolExecutor(max_workers=MAX_RUNNING, thread_name_prefix="learnai-task")


def _update(task_id: str, **fields) -> None:
    with _lock:
        _tasks[task_id][1].update(fields, updated=time.time())


def _prune() -> None:
    cutoff = time.time() - TASK_TTL_SECONDS
    with _lock:
        for task_id in [t for t, (_, task) in _tasks.items()
                        if task["status"] in ("done", "failed") and task["updated"] < cutoff]:
            del _tasks[task_id]


def _run(task_id: str, kind: str, job: Callable[[Report], dict]) -> None:
    def report(stage: str, progress: Optional[float] = None, title: Optional[str] = None) -> None:
        _update(task_id, status="running", stage=stage, progress=progress,
                **({"title": title} if title else {}))

    _update(task_id, status="running")
    try:
        result = job(report)
    except Exception as e:
        logger.exception(f"Task {task_id} ({kind}) failed")
        _update(task_id, status="failed", error=str(e))
        return
    _update(task_id, status="done", stage="done", progress=1.0, result=result,
            **({"title": result["title"]} if result.get("title") else {}))


def start_task(user_id: str, kind: str, job: Callable[[Report], dict]) -> dict:
    """Run job(report) in the background; it calls report() as it goes and returns the result."""
    _prune()
    task_id = uuid.uuid4().hex
    task = {"task_id": task_id, "kind": kind, "status": "queued", "stage": "queued", "progress": None,
            "title": None, "result": None, "error": None, "updated": time.time()}
    with _lock:
        _tasks[task_id] = (user_id, task)
    _pool.submit(_run, task_id, kind, job)
    return get_task(task_id, user_id)


def get_task(task_id: str, user_id: str) -> Optional[dict]:
    with _lock:
        owner, task = _tasks.get(task_id, (None, None))
        if owner != user_id:
            return None
        return {k: v for k, v in task.items() if k != "updated"}
