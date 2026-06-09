"""FastAPI server: REST API layer for CS599 backend."""
import sys
import os
from pathlib import Path

# Ensure project root is on sys.path
_project_root = Path(__file__).parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.api.routers import assistant, generation, agents, providers, skills, history, mcp, search
from src.api.routers.download import router as download_router
from src.api.routers.export import router as export_router
from src.api.cancel import mark_cancelled

app = FastAPI(title="CS599 Research Assistant API", version="2.0.0")

# CORS: allow dev origins and production same-origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global exception handler ──────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all unhandled exceptions and return a structured JSON error."""
    exc_name = type(exc).__name__
    exc_msg = str(exc)

    # Determine appropriate HTTP status code
    if "AuthenticationError" in exc_name or "401" in exc_msg:
        status_code = 401
    elif "ValueError" in exc_name:
        status_code = 400
    else:
        status_code = 500

    return JSONResponse(
        status_code=status_code,
        content={
            "detail": exc_msg,
            "error_type": exc_name,
            "message": f"后端处理请求时出错: {exc_msg[:200]}",
        },
    )

# Register API routers
app.include_router(assistant.router)
app.include_router(generation.router)
app.include_router(agents.router)
app.include_router(providers.router, prefix="/api")
app.include_router(skills.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(mcp.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(download_router)
app.include_router(export_router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}


# ── Request cancellation ───────────────────────────────────────────────────
@app.post("/api/cancel/{request_id}")
async def cancel_request(request_id: str):
    """Mark a running request as cancelled.  The skill execution code polls
    this flag cooperatively and stops as soon as possible."""
    mark_cancelled(request_id)
    return {"status": "ok", "message": f"Request {request_id} cancellation signalled"}


# Serve React static files in production (dist/ exists)
_dist_dir = _project_root / "frontend" / "dist"
if _dist_dir.exists():
    app.mount("/", StaticFiles(directory=str(_dist_dir), html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.server:app", host="0.0.0.0", port=8000, reload=True)