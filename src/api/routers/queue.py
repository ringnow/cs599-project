"""API routes for async task queue."""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional

from src.queue.worker import enqueue_task, get_task_status, get_task_result

router = APIRouter(tags=["queue"])


class AsyncResearchRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=500)
    task_type: str = Field(default="research")
    provider: str = Field(default="")
    model_id: str = Field(default="")
    depth: int = Field(default=3, ge=1, le=5)
    sources: Optional[list] = Field(default=["web", "semantic_scholar"])


class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str


@router.post("/api/queue/research", response_model=TaskResponse)
def enqueue_research(req: AsyncResearchRequest, request: Request):
    """Submit a research task to the async queue. Returns task_id immediately."""
    # Carry the JWT-authenticated username so async tasks stay user-attributed.
    user_id = getattr(request.state, "user", "") or ""
    task_id = enqueue_task(req.task_type, {
        "topic": req.topic,
        "provider": req.provider,
        "model_id": req.model_id,
        "depth": req.depth,
        "sources": req.sources,
        "user_id": user_id,
    })
    if task_id is None:
        raise HTTPException(status_code=503, detail="Redis not available, async queue unavailable. Use /api/report for sync mode.")
    return TaskResponse(task_id=task_id, status="queued", message="Task submitted. Poll /api/queue/status/{task_id}")


@router.get("/api/queue/status/{task_id}")
def task_status(task_id: str):
    """Check task status and progress."""
    status = get_task_status(task_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Task not found or Redis unavailable")
    return status


@router.get("/api/queue/result/{task_id}")
def task_result(task_id: str):
    """Get completed task result."""
    status = get_task_status(task_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if status["status"] not in ("completed", "failed"):
        return {"ready": False, "status": status["status"], "progress": status.get("progress", 0)}

    # Failed tasks carry the error in the status object; surface it so
    # clients polling /result learn the task is terminally done.
    if status["status"] == "failed":
        return {
            "ready": True,
            "status": "failed",
            "error": status.get("error", "Task failed without error message"),
        }

    result = get_task_result(task_id)
    if result is None:
        return {"ready": False, "status": status["status"], "message": "Result not yet available"}
    return {"ready": True, "status": status["status"], "data": result}
