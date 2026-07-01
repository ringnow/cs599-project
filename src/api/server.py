"""FastAPI server: REST API layer for CS599 backend."""
import sys
import os
import asyncio
import mimetypes
from contextlib import asynccontextmanager
from pathlib import Path

# 加载 .env 环境变量（必须在其他模块 import 之前执行，否则 REDIS_URL / DATABASE_URL
# 等配置会在模块导入时被读取为默认值，导致配置不生效）
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Windows 默认不注册 .js/.mjs 的 MIME type，导致浏览器拒绝加载模块脚本
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/javascript", ".mjs")
mimetypes.add_type("text/css", ".css")

# Ensure project root is on sys.path
_project_root = Path(__file__).parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import assistant, generation, agents, providers, skills, history, mcp, search
from src.api.routers.download import router as download_router
from src.api.routers.export import router as export_router
from src.api.cancel import mark_cancelled
from src.api.routers.search_history import router as search_history_router
from src.api.middleware import JWTAuthMiddleware
from src.api.routers.auth import router as auth_router
from src.api.routers.cache import router as cache_router
from src.api.routers.queue import router as queue_router
from src.api.routers.knowledge import router as knowledge_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: runs startup logic, yields, then shutdown.

    Replaces the deprecated @app.on_event("startup"/"shutdown") pair.

    所有阻塞型同步调用（init_db / ensure_admin_user / start_worker）都通过
    asyncio.to_thread 放到独立线程执行，避免阻塞事件循环导致启动卡死。
    """
    import logging
    _log = logging.getLogger("cs599.server")

    # ── Startup ──
    from src.storage.database import init_db, SessionLocal, ensure_admin_user

    # init_db() 内部执行 create_all，是同步阻塞调用；放到线程池执行
    await asyncio.to_thread(init_db)

    # ensure_admin_user 涉及 bcrypt 哈希（CPU 密集），同样放线程池
    def _ensure_admin():
        db = SessionLocal()
        try:
            ensure_admin_user(db)
        finally:
            db.close()
    await asyncio.to_thread(_ensure_admin)

    # start_worker 启动后台消费线程（非阻塞，但内部若失败不应卡住启动）
    from src.task_queue.worker import start_worker
    from src.task_queue.handler import handle_task
    await asyncio.to_thread(start_worker, handle_task)

    _log.info("启动完成：数据库初始化 + 管理员用户 + 队列 worker 已就绪")

    yield  # application runs here

    # ── Shutdown ──
    from src.task_queue.worker import stop_worker
    await asyncio.to_thread(stop_worker)
    _log.info("已停止队列 worker")


app = FastAPI(title="CS599 Research Assistant API", version="2.0.0", lifespan=lifespan)

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

# JWT Auth middleware (non-blocking: routes run without token, but get user info if present)
app.add_middleware(JWTAuthMiddleware)


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
app.include_router(search_history_router)
app.include_router(auth_router)
app.include_router(cache_router)
app.include_router(queue_router)
app.include_router(knowledge_router)


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
    # Map file extensions to correct MIME types (Windows workaround)
    CONTENT_TYPES = {
        ".html": "text/html; charset=utf-8",
        ".js": "text/javascript; charset=utf-8",
        ".mjs": "text/javascript; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".json": "application/json",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".svg": "image/svg+xml",
        ".ico": "image/x-icon",
        ".woff": "font/woff",
        ".woff2": "font/woff2",
    }

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serve React static files with correct MIME types."""
        # Skip API routes — they are handled by routers above
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")

        file_path = _dist_dir / full_path

        # SPA fallback: non-existent paths → index.html
        if not file_path.is_file():
            file_path = _dist_dir / "index.html"
            if not file_path.exists():
                raise HTTPException(status_code=404, detail="Frontend not built")

        ext = file_path.suffix.lower()
        media_type = CONTENT_TYPES.get(ext, "application/octet-stream")
        return FileResponse(str(file_path), media_type=media_type)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.server:app", host="0.0.0.0", port=8000, reload=True)