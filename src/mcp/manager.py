"""MCP Server Manager — dynamic add/remove/configure MCP servers.

Supports:
- Tavily MCP (AI search engine) via stdio transport with proxy
- Custom MCP servers via SSE/stdio transport
- Enable/disable per server
- Embedded Tavily MCP Server startup via subprocess

MCP Usage (correct way):
- Tavily MCP Server is a stdio-mode server
- Use mcp.ClientSession + stdio_client to connect
- NOT HTTP/SSE direct calls
"""
import asyncio
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict

from src.models.key_store import get_key_store

# MCP Python SDK imports
HAS_MCP_SDK = False
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.client.sse import sse_client
    HAS_MCP_SDK = True
except ImportError:
    pass

# Config storage
MCP_CONFIG_DIR = Path.home() / ".cs599-agent"
MCP_CONFIG_FILE = MCP_CONFIG_DIR / "mcp_servers.json"


@dataclass
class MCPServerConfig:
    """Configuration for a single MCP server."""
    name: str
    display_name: str
    url: str  # SSE endpoint URL, e.g., http://localhost:7980/sse
    api_key_env: str = ""  # Environment variable name for API key
    api_key: str = ""
    tools_prefix: str = ""  # Prefix for tool names, e.g., "tavily_"
    description: str = ""
    is_active: bool = True
    server_type: str = "sse"  # "sse" or "stdio"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> 'MCPServerConfig':
        known = set(cls.__dataclass_fields__.keys())
        d = {k: v for k, v in d.items() if k in known}
        return cls(**d)


# Built-in MCP server presets
BUILTIN_MCP_PRESETS = {
    "tavily_stdio": MCPServerConfig(
        name="tavily_stdio",
        display_name="Tavily Search (本地stdio)",
        url="http://localhost:7980/sse",
        api_key_env="TAVILY_API_KEY",
        tools_prefix="tavily_",
        description="Tavily AI 搜索引擎 — 本地 npx stdio 启动（需代理）",
        server_type="stdio",
    ),
    "tavily": MCPServerConfig(
        name="tavily",
        display_name="Tavily Search (远程SSE) ★推荐",
        url="https://mcp.tavily.com/sse",
        api_key_env="TAVILY_API_KEY",
        tools_prefix="tavily_",
        description="Tavily AI 搜索引擎 — 远程 SSE 模式，输入 URL 和 API Key 即可使用（走代理）",
        server_type="sse",
    ),
    "playwright": MCPServerConfig(
        name="playwright",
        display_name="Playwright (浏览器自动化)",
        url="http://localhost:3000/sse",
        tools_prefix="browser_",
        description="Playwright MCP Server，用于网页内容提取和浏览器自动化",
    ),
    "filesystem": MCPServerConfig(
        name="filesystem",
        display_name="Filesystem (文件系统)",
        url="http://localhost:3001/sse",
        tools_prefix="fs_",
        description="文件系统操作 MCP Server",
    ),
}


class MCPManager:
    """Manages MCP servers — add, remove, configure, health check."""

    def __init__(self):
        self._servers: Dict[str, MCPServerConfig] = {}
        self._key_store = get_key_store()
        self._tavily_process: Optional[subprocess.Popen] = None
        self._load()

    def _load(self):
        """Load MCP server configs from file."""
        if MCP_CONFIG_FILE.exists():
            try:
                data = json.loads(MCP_CONFIG_FILE.read_text())
                for name, server_data in data.items():
                    self._servers[name] = MCPServerConfig.from_dict(server_data)
            except Exception:
                pass

    def _save(self):
        """Save MCP server configs to file."""
        MCP_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {name: s.to_dict() for name, s in self._servers.items()}
        MCP_CONFIG_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    # ---- CRUD ----

    def list_servers(self) -> List[MCPServerConfig]:
        """List all configured MCP servers."""
        return list(self._servers.values())

    def get_server(self, name: str) -> Optional[MCPServerConfig]:
        return self._servers.get(name)

    def add_from_preset(self, preset_name: str, custom_url: str = "",
                        api_key: str = "") -> tuple[bool, str]:
        """Add an MCP server from a preset."""
        preset = BUILTIN_MCP_PRESETS.get(preset_name)
        if not preset:
            return False, f"预设 '{preset_name}' 不存在"

        config = MCPServerConfig(
            name=preset.name,
            display_name=preset.display_name,
            url=custom_url or preset.url,
            api_key_env=preset.api_key_env,
            api_key=api_key,
            tools_prefix=preset.tools_prefix,
            description=preset.description,
            is_active=True,
        )
        self._servers[config.name] = config
        self._save()
        return True, f"已添加 MCP Server '{config.display_name}' ({config.url})"

    def add_custom(self, name: str, display_name: str, url: str,
                   api_key: str = "", tools_prefix: str = "") -> tuple[bool, str]:
        """Add a custom MCP server."""
        if not name or not url:
            return False, "名称和 URL 不能为空"

        config = MCPServerConfig(
            name=name, display_name=display_name or name,
            url=url, api_key=api_key, tools_prefix=tools_prefix,
            is_active=True,
        )
        self._servers[name] = config
        self._save()
        return True, f"已添加 MCP Server '{name}' ({url})"

    def remove(self, name: str) -> bool:
        """Remove an MCP server."""
        if name in self._servers:
            del self._servers[name]
            self._save()
            return True
        return False

    def update(self, name: str, **kwargs) -> bool:
        """Update an MCP server config."""
        if name not in self._servers:
            return False
        cfg = self._servers[name]
        for key, value in kwargs.items():
            if hasattr(cfg, key):
                setattr(cfg, key, value)
        self._save()
        return True

    def toggle(self, name: str) -> bool:
        """Toggle active status."""
        if name in self._servers:
            self._servers[name].is_active = not self._servers[name].is_active
            self._save()
            return True
        return False

    # ---- Health Check ----

    def health_check(self, name: str) -> tuple[bool, str]:
        """Check if MCP server is reachable."""
        cfg = self._servers.get(name)
        if not cfg:
            return False, "Server not found"
        if not cfg.is_active:
            return False, "Disabled"

        # stdio servers: check process or just return configured status
        # (don't HTTP GET localhost addresses that may not be running)
        if cfg.server_type == "stdio":
            if name == "tavily":
                running = self.is_tavily_running()
                return running, f"进程{'运行中' if running else '未启动'}"
            return True, "stdio (启动后可用)"

        # SSE servers: HTTP GET check
        try:
            resp = httpx.get(cfg.url, timeout=5.0)
            return resp.status_code < 500, f"HTTP {resp.status_code}"
        except Exception as e:
            return False, str(e)[:100]

    # ---- Tavily Server Process Management ----

    def start_tavily_server(self, tavily_api_key: str = "",
                            proxy: str = "http://localhost:7980") -> tuple[bool, str]:
        """Start Tavily MCP Server via npx subprocess with proxy settings.

        Args:
            tavily_api_key: Tavily API Key (optional, will also check env)
            proxy: HTTP proxy URL, e.g. http://localhost:7980

        Returns:
            (success, message)
        """
        # Check if already running
        if self._tavily_process is not None and self._tavily_process.poll() is None:
            return True, f"Tavily MCP Server 已在运行 (PID: {self._tavily_process.pid})"

        # Prepare environment
        env = os.environ.copy()
        if proxy:
            env["HTTP_PROXY"] = proxy
            env["HTTPS_PROXY"] = proxy
            env["http_proxy"] = proxy
            env["https_proxy"] = proxy

        # API Key priority: parameter > key_store > env
        key = tavily_api_key or self._key_store.get_key("tavily") or os.environ.get("TAVILY_API_KEY", "")
        if key:
            env["TAVILY_API_KEY"] = key

        try:
            # Start Tavily MCP Server via npx
            cmd = ["npx", "-y", "@tavily/mcp@latest"]
            self._tavily_process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(MCP_CONFIG_DIR),
            )
            # Wait briefly to check if it started successfully
            time.sleep(2)
            if self._tavily_process.poll() is not None:
                # Process exited early
                stderr = ""
                try:
                    if self._tavily_process.stderr:
                        stderr = self._tavily_process.stderr.read(500).decode('utf-8', errors='ignore')
                except Exception:
                    pass
                self._tavily_process = None
                return False, f"Tavily MCP Server 启动失败 (进程提前退出): {stderr}"

            return True, f"Tavily MCP Server 已启动 (PID: {self._tavily_process.pid})，代理: {proxy}"
        except FileNotFoundError:
            return False, "找不到 npx 命令，请先安装 Node.js"
        except Exception as e:
            self._tavily_process = None
            return False, f"启动失败: {e}"

    def stop_tavily_server(self) -> tuple[bool, str]:
        """Stop the embedded Tavily MCP Server."""
        if self._tavily_process is None:
            return False, "Tavily MCP Server 未运行"

        try:
            self._tavily_process.terminate()
            try:
                self._tavily_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._tavily_process.kill()
                self._tavily_process.wait()
            self._tavily_process = None
            return True, "Tavily MCP Server 已停止"
        except Exception as e:
            return False, f"停止失败: {e}"

    def is_tavily_running(self) -> bool:
        """Check if Tavily MCP Server process is running."""
        if self._tavily_process is None:
            return False
        return self._tavily_process.poll() is None

    def get_tavily_status(self) -> dict:
        """Get detailed status of Tavily MCP Server."""
        running = self.is_tavily_running()
        return {
            "running": running,
            "pid": self._tavily_process.pid if running else None,
            "server_configured": "tavily" in [s.name for s in self.list_servers()],
        }

    # ---- Async MCP Tool Calling (correct stdio way) ----

    async def _call_tool_async(self, server_name: str, tool_name: str,
                                arguments: dict) -> dict:
        """Async tool call using MCP stdio_client or sse_client."""
        cfg = self._servers.get(server_name)
        if not cfg or not cfg.is_active:
            return {"error": f"MCP Server '{server_name}' not available"}

        if not HAS_MCP_SDK:
            return {"error": "mcp Python SDK not installed. Run: pip install mcp"}

        if cfg.server_type == "sse" or cfg.url.startswith("https://"):
            return await self._call_via_sse(cfg, tool_name, arguments)
        else:
            return await self._call_via_stdio(cfg, tool_name, arguments)

    async def _call_via_sse(self, cfg: MCPServerConfig, tool_name: str,
                            arguments: dict) -> dict:
        """Call tool via SSE transport (for remote MCP servers like Tavily)."""
        try:
            # Build headers with API key
            headers = {}
            key = cfg.api_key or self._key_store.get_key("tavily") or os.environ.get("TAVILY_API_KEY", "")
            if not key:
                return {"error": "Tavily API Key 未配置。请在「服务商管理」→「搜索工具 API Key」中配置 TAVILY_API_KEY"}
            headers["Authorization"] = f"Bearer {key}"

            async with sse_client(cfg.url, headers=headers) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, arguments=arguments)
                    return self._parse_tool_result(result)
        except Exception as e:
            return {"error": f"SSE MCP 调用失败: {e}"}

    async def _call_via_stdio(self, cfg: MCPServerConfig, tool_name: str,
                              arguments: dict) -> dict:
        """Call tool via stdio transport (for local MCP servers)."""
        try:
            if cfg.tools_prefix == "tavily_":
                # Tavily stdio via npx
                env = os.environ.copy()
                proxy_url = cfg.url.replace("/sse", "") if cfg.url.endswith("/sse") else cfg.url
                env["HTTP_PROXY"] = proxy_url
                env["HTTPS_PROXY"] = proxy_url
                env["http_proxy"] = proxy_url
                env["https_proxy"] = proxy_url
                key = cfg.api_key or self._key_store.get_key("tavily") or os.environ.get("TAVILY_API_KEY", "")
                if not key:
                    return {"error": "Tavily API Key 未配置"}
                env["TAVILY_API_KEY"] = key

                server_params = StdioServerParameters(
                    command="npx",
                    args=["-y", "@tavily/mcp@latest"],
                    env=env,
                )
            else:
                return {"error": f"stdio transport not supported for: {cfg.name}"}

            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, arguments=arguments)
                    return self._parse_tool_result(result)
        except Exception as e:
            return {"error": f"stdio MCP 调用失败: {e}"}

    @staticmethod
    def _parse_tool_result(result) -> dict:
        """Parse MCP tool result into a dict."""
        try:
            content_blocks = []
            if hasattr(result, 'content') and result.content:
                for block in result.content:
                    if hasattr(block, 'text'):
                        content_blocks.append(block.text)

            # Try to parse as JSON
            try:
                parsed = json.loads(content_blocks[0]) if content_blocks else {}
                return {"result": parsed, "raw": content_blocks}
            except json.JSONDecodeError:
                return {"result": content_blocks, "raw": content_blocks}
        except Exception as e:
            return {"error": f"解析 MCP 结果失败: {e}"}

    def call_tool(self, server_name: str, tool_name: str, arguments: dict) -> dict:
        """Call a tool on an MCP server (sync wrapper around async)."""
        import concurrent.futures

        def _run_async():
            """Run async call in a fresh event loop."""
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                return loop.run_until_complete(
                    self._call_tool_async(server_name, tool_name, arguments)
                )
            finally:
                loop.close()

        try:
            # Check if there's already a running event loop
            loop = asyncio.get_running_loop()
            if loop:
                # Use thread pool with fresh loop
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(_run_async)
                    try:
                        return future.result(timeout=60)
                    except concurrent.futures.TimeoutError:
                        return {"error": "MCP call timed out (60s)"}
                    except Exception as te:
                        return {"error": f"MCP thread error: {te}"}
        except RuntimeError:
            # No running event loop — use asyncio.run directly
            pass

        try:
            return asyncio.run(self._call_tool_async(server_name, tool_name, arguments))
        except RuntimeError as e:
            if "already running" in str(e) or "cannot be called from a running loop" in str(e):
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(_run_async)
                    try:
                        return future.result(timeout=60)
                    except concurrent.futures.TimeoutError:
                        return {"error": "MCP call timed out (60s)"}
                    except Exception as te:
                        return {"error": f"MCP thread error: {te}"}
            return {"error": f"Async runtime error: {e}"}
        except Exception as e:
            return {"error": f"MCP tool call error: {e}"}

    # ---- Search Integration ----

    def search(self, query: str, max_results: int = 5) -> List[dict]:
        """Search using Tavily MCP Server via stdio transport."""
        results = []
        for cfg in self._servers.values():
            if not cfg.is_active:
                continue
            if cfg.tools_prefix == "tavily_":
                result = self.call_tool(cfg.name, "search", {
                    "query": query,
                    "max_results": max_results,
                })
                if "error" not in result:
                    # Parse result — could be in 'result' or 'raw' key
                    parsed = result.get("result", result.get("raw", []))
                    if isinstance(parsed, list):
                        results.extend(parsed)
                    elif isinstance(parsed, dict) and "results" in parsed:
                        results.extend(parsed["results"])
        return results


# Singleton
_mcp_manager = None


def get_mcp_manager() -> MCPManager:
    global _mcp_manager
    if _mcp_manager is None:
        _mcp_manager = MCPManager()
    return _mcp_manager
