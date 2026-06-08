"""GET/POST/DELETE /api/mcp — MCP server management."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from src.mcp.manager import get_mcp_manager

router = APIRouter()


class MCPAddRequest(BaseModel):
    name: str
    display_name: str
    url: str
    api_key: str = ""
    tools_prefix: str = ""
    server_type: str = "sse"


class TavilyStartRequest(BaseModel):
    api_key: str
    proxy: Optional[str] = None


@router.get("/mcp/servers")
async def list_mcp_servers():
    mgr = get_mcp_manager()
    servers = mgr.list_servers()
    return [
        {
            "name": s.name,
            "display_name": s.display_name,
            "server_type": s.server_type,
            "is_active": s.is_active,
            "tools_prefix": s.tools_prefix,
        }
        for s in servers
    ]


@router.post("/mcp/servers")
async def add_mcp_server(req: MCPAddRequest):
    mgr = get_mcp_manager()
    try:
        mgr.add_custom(req.name, req.display_name, req.url, req.api_key, req.tools_prefix, req.server_type)
        return {"status": "ok", "message": f"MCP 服务器 {req.name} 已添加"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/mcp/servers/{name}")
async def delete_mcp_server(name: str):
    mgr = get_mcp_manager()
    try:
        mgr.remove(name)
        return {"status": "ok", "message": f"MCP 服务器 {name} 已删除"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/mcp/servers/{name}/toggle")
async def toggle_mcp(name: str):
    mgr = get_mcp_manager()
    try:
        mgr.toggle(name)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/mcp/servers/{name}/health")
async def mcp_health(name: str):
    mgr = get_mcp_manager()
    try:
        healthy = mgr.health_check(name)
        return {"name": name, "healthy": healthy}
    except Exception as e:
        return {"name": name, "healthy": False, "error": str(e)}


@router.post("/mcp/tavily/start")
async def start_tavily(req: TavilyStartRequest):
    mgr = get_mcp_manager()
    try:
        mgr.start_tavily_server(req.api_key, req.proxy)
        return {"status": "ok", "message": "Tavily MCP 服务器已启动"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/mcp/tavily/stop")
async def stop_tavily():
    mgr = get_mcp_manager()
    mgr.stop_tavily_server()
    return {"status": "ok", "message": "Tavily MCP 服务器已停止"}


@router.get("/mcp/tavily/status")
async def tavily_status():
    mgr = get_mcp_manager()
    return {"running": mgr.is_tavily_running()}


@router.post("/mcp/stdio/{name}/start")
async def start_stdio(name: str):
    """Start a generic stdio MCP server (filesystem_stdio, memory_stdio, etc.)."""
    mgr = get_mcp_manager()
    try:
        success, msg = mgr.start_stdio_server(name)
        if not success:
            raise HTTPException(status_code=400, detail=msg)
        return {"status": "ok", "message": msg}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/mcp/stdio/{name}/stop")
async def stop_stdio(name: str):
    """Stop a generic stdio MCP server."""
    mgr = get_mcp_manager()
    try:
        success, msg = mgr.stop_stdio_server(name)
        if not success:
            raise HTTPException(status_code=400, detail=msg)
        return {"status": "ok", "message": msg}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/mcp/stdio/{name}/status")
async def stdio_status(name: str):
    """Check if a generic stdio MCP server is running."""
    mgr = get_mcp_manager()
    try:
        running = mgr.is_stdio_running(name)
        return {"name": name, "running": running}
    except Exception as e:
        return {"name": name, "running": False, "error": str(e)}


@router.get("/mcp/stdio/servers")
async def list_stdio_servers():
    """List all stdio MCP servers with running status."""
    mgr = get_mcp_manager()
    return mgr.list_stdio_servers()