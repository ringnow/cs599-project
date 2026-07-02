"""POST /api/report, /api/outline, /api/thesis, /api/literature-review — Generation endpoints."""
from datetime import datetime
from typing import List, Any

from fastapi import APIRouter, Request
from src.models.manager import get_model_manager
from src.models.key_store import get_key_store
from src.skills.registry import get_skill_registry
from src.skills.base import SkillContext
from src.api.schemas import ReportRequest, OutlineRequest, ThesisRequest, ReviewRequest, ApiResponse
from src.api.dependencies import resolve_provider_model, has_api_key
import asyncio
import concurrent.futures

router = APIRouter()


def _format_error(e: Exception) -> str:
    """Extract the full error chain including __cause__ for ConnectionError etc.

    openai.APIConnectionError str() is just 'Connection error.' — the actual
    SSL/DNS cause lives in __cause__. This surfaces it for diagnosis.
    """
    parts = [str(e)]
    cause = getattr(e, "__cause__", None) or getattr(e, "__context__", None)
    if cause and str(cause) not in str(e):
        parts.append(f" (cause: {cause})")
    # For APIConnectionError, also show the error type
    etype = type(e).__name__
    if etype != "Exception":
        parts.append(f" [{etype}]")
    return "".join(parts)[:500]


def _mcp_enhance(mcp_servers: List[str], topic: str) -> tuple:
    """通用 MCP 预搜索：按类型调用各 MCP 服务器，返回 context + logs。

    支持 4 种免费 MCP：
    - fetch → arxiv API 搜论文 → 解析 Atom XML
    - filesystem → 扫 research_outputs/ 目录 → 读取已有报告
    - memory → search_nodes 查历史知识图谱
    - sequential-thinking → 主题拆解 → 返回子问题列表
    """
    if not mcp_servers:
        return "", []
    logs = []
    try:
        from src.mcp.manager import get_mcp_manager
        mgr = get_mcp_manager()
        snippets = []

        for srv_name in mcp_servers:
            if not mgr.is_server_enabled(srv_name):
                logs.append(f"  ⏭️ MCP {srv_name} 未启用，跳过")
                continue

            logs.append(f"🔌 正在调用 MCP 服务器: {srv_name}")

            try:
                if "fetch" in srv_name:
                    # arxiv API 搜索
                    fetch_url = f"https://export.arxiv.org/api/query?search_query=all:{topic}&max_results=3&sortBy=relevance&sortOrder=descending"
                    r = mgr.call_tool(srv_name, "fetch", {"url": fetch_url})
                    papers = _parse_arxiv_xml(r)
                    for p in papers:
                        snippets.append(f"[arxiv] {p}")
                    logs.append(f"  ✅ MCP fetch → arxiv: {len(papers)} 篇论文")

                elif "filesystem" in srv_name:
                    # 扫本地产物目录
                    r = mgr.call_tool(srv_name, "list_directory", {"path": "./research_outputs"})
                    raw = r.get("result", r.get("raw", ""))
                    items = raw if isinstance(raw, list) else []
                    matching = [item for item in items if isinstance(item, str) and topic.lower() in item.lower()]
                    for item in matching[:5]:
                        snippets.append(f"[本地文件] {item}")
                    logs.append(f"  ✅ MCP filesystem: 扫描到 {len(matching)} 个相关文件")

                elif "memory" in srv_name:
                    # 查历史知识图谱
                    r = mgr.call_tool(srv_name, "search_nodes", {"query": topic})
                    raw = r.get("result", r.get("raw", ""))
                    if isinstance(raw, dict) and raw.get("entities"):
                        for ent in raw["entities"][:3]:
                            name = ent.get("name", "")
                            obs = "; ".join(ent.get("observations", [])[:2])
                            snippets.append(f"[记忆] {name}: {obs[:200]}")
                    logs.append(f"  ✅ MCP memory: 查询知识图谱完成")

                elif "sequential" in srv_name:
                    # 分步推理
                    r = mgr.call_tool(srv_name, "sequentialthinking",
                                      {"thought": f"Research topic: {topic}. Break down into sub-questions."})
                    raw = r.get("result", r.get("raw", ""))
                    if isinstance(raw, dict) and raw.get("thought"):
                        snippets.append(f"[推理] {raw['thought'][:300]}")
                    logs.append(f"  ✅ MCP sequential-thinking: 推理完成")

                else:
                    # 通用 fallback：调 search 工具
                    r = mgr.call_tool(srv_name, "search", {"query": topic, "max_results": 3})
                    if "error" not in r:
                        parsed = r.get("result", r.get("raw", []))
                        items = parsed.get("results", parsed) if isinstance(parsed, dict) else (parsed if isinstance(parsed, list) else [])
                        count = 0
                        for item in (items if isinstance(items, list) else [items]):
                            if isinstance(item, dict):
                                snippets.append(f"- {item.get('title','')}: {item.get('content',item.get('snippet',''))[:200]}")
                                count += 1
                        logs.append(f"  ✅ MCP {srv_name} 返回 {count} 条结果")
                    else:
                        logs.append(f"  ⚠️ MCP {srv_name} 调用错误: {r['error'][:100]}")

            except Exception as e:
                logs.append(f"  ⚠️ MCP {srv_name} 异常: {str(e)[:100]}")
                pass

        context = "\nMCP搜索结果：\n" + "\n".join(snippets[:10]) if snippets else ""
        return context, logs
    except Exception as e:
        return "", [f"❌ MCP 管理器错误: {str(e)[:100]}"]


def _parse_arxiv_xml(raw: Any) -> List[str]:
    """解析 arxiv Atom XML 响应 → 论文摘要列表。"""
    try:
        import xml.etree.ElementTree as ET
        result = raw.get("result", "") if isinstance(raw, dict) else str(raw)
        root = ET.fromstring(result)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        papers = []
        for entry in root.findall("atom:entry", ns):
            title = entry.findtext("atom:title", "", ns).strip().replace("\n", " ").replace("  ", " ")
            summary = entry.findtext("atom:summary", "", ns).strip()[:300].replace("\n", " ")
            link = entry.findtext("atom:id", "", ns)
            published = entry.findtext("atom:published", "", ns)[:10]
            papers.append(f"{title} ({published}) - {summary[:150]}... | {link}")
        return papers
    except Exception:
        return []


def _execute_skill(actual: str, topic: str, provider: str, model: str, params: dict, user_id: str = ""):
    """Execute a skill and return markdown string + steps."""
    ctx = SkillContext(topic=topic, provider_name=provider, model_id=model, custom_params=params, user_id=user_id)
    sr = get_skill_registry().execute(actual, ctx)
    if sr.success:
        return sr.content, sr.steps
    return f"技能执行失败: {sr.error}", sr.steps


async def _execute_skill_with_timeout(actual: str, topic: str, provider: str, model: str, params: dict, timeout: int = 600, user_id: str = ""):
    """Execute a skill with a timeout to prevent hanging.

    Runs the blocking skill code in a thread pool so the async event loop
    is NOT blocked during long-running research tasks.

    Returns:
        Tuple of (content: str, steps: list). On timeout, both are populated
        with an error message and empty steps (NOT a bare string, to avoid
        unpacking bugs when callers do ``content, steps = await ...``).
    """
    loop = asyncio.get_event_loop()
    try:
        return await asyncio.wait_for(
            loop.run_in_executor(None, _execute_skill, actual, topic, provider, model, params, user_id),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        return f"技能执行超时（{timeout}秒）。请检查服务商配置和网络连接。", []


def _demo_content(topic: str, task_type: str) -> str:
    """Return demo content when no API key is configured."""
    return f"""### 演示模式 — 未配置 API Key

> **⚠️ 警告：演示模式** — 以下内容由 AI 自动生成，其中的参考文献为模拟示例，**并非真实学术论文**。请勿将其用于实际学术引用或研究用途。如需真实引用，请在「服务商管理」中配置有效的 API Key。

当前正在处理主题：**{topic}**

---

#### 1. 前沿挑战与研究现状

在计算科学与人工智能的交叉领域，**{topic}** 的研究正在经历范式转变。基于深度表示学习和自适应对齐的模型能够解决长上下文建模、计算稳定性约束与跨域零样本迁移等核心痛点。

#### 2. 核心学术架构设计

- **感知对齐层 (Perceptual Alignment Layer)**: 对多源异构输入进行归一化处理
- **博弈演化模块 (Evolutionary Game Module)**: 通过模拟自适应网络转移函数，实现分布式智能体间的局部纳什对齐
- **可解释性自回归模型 (Explainable Auto-regressive Logic)**: 增加可解释注意力张量的权重分布，帮助追踪决策归因

#### 3. 领域经典参考文献（⚠️ 以下为演示示例，非真实数据）

1. **[演示示例] Zhang, Y., & Wang, H. (2025).** "Scalable Deep Autoencoders for Multi-agent Coordination and Federated Topologies." *Journal of Machine Learning Research (JMLR)*, vol. 26, pp. 112-134.
2. **[演示示例] Li, S., et al. (2025).** "Decentralized Optimal Control with Deep Implicit Layers." *IEEE Transactions on Pattern Analysis and Machine Intelligence (TPAMI)*, vol. 47, no. 3, pp. 1024-1039.

---

> 提示：请在「服务商管理」中配置有效的 API Key 以启用实时的 AI 学术大模型生成。
> 支持的提供商：DeepSeek、OpenAI、Anthropic、硅基流动、OpenRouter 等。
"""


@router.post("/api/report", response_model=ApiResponse)
async def report(req: ReportRequest, request: Request):
    logs = ["初始化学术报告生成器...", f"分析研究领域: {req.field or '通用'}", f"生成深度: {req.depth}"]
    try:
        depth_map = {"基础": 1, "详细": 3, "专家": 5}
        provider, model = resolve_provider_model(req.provider, req.model)
        user_id = getattr(request.state, "user", "") or ""

        if not has_api_key(provider):
            logs.append("未检测到 API Key，切换至演示模式")
            return ApiResponse(logs=logs, markdown=_demo_content(req.subject, "report"))

        mcp_ctx = ""
        if req.mcp_servers:
            mcp_ctx, mcp_logs = _mcp_enhance(req.mcp_servers, req.subject)
            logs.extend(mcp_logs)

        context = req.context or req.field
        if mcp_ctx:
            context = (context or "") + mcp_ctx

        actual = req.skill_override if req.skill_override else "research"
        content, steps = await _execute_skill_with_timeout(actual, req.subject, provider, model, {
            "depth": depth_map.get(req.depth, 3),
            "sources": ["web", "semantic_scholar"],
            "context": context or req.field,
            "reference_count": req.referenceCount,
            "include_charts": req.includeCharts,
            "request_id": req.request_id,
        }, timeout=600, user_id=user_id)
        logs.append("报告生成完成！")

        # Format steps for display
        step_logs = []
        for s in steps:
            status_icon = {"done": "✅", "running": "⏳", "error": "❌", "warning": "⚠️"}.get(s.get("status", ""), "➖")
            action = s.get("action", "")
            query = s.get("query", "")
            result = s.get("result", "")
            step_logs.append(f"{status_icon} [{action}] {query[:60] if query else action} {result[:80] if result else ''}")

        from src.api.routers.history import save_report
        save_report("report", req.subject, content)
        return ApiResponse(logs=logs + step_logs, markdown=content, steps=steps)
    except Exception as e:
        logs.append(f"❌ 报告生成出错: {_format_error(e)}")
        return ApiResponse(logs=logs, markdown=f"### ⚠️ 报告生成失败\n\n**错误**: {_format_error(e)}\n\n请检查服务商配置。")


@router.post("/api/outline", response_model=ApiResponse)
async def outline(req: OutlineRequest, request: Request):
    logs = ["正在调研相关领域...", "正在进行论文构思..."]
    try:
        provider, model = resolve_provider_model(req.provider, req.model)

        if not has_api_key(provider):
            logs.append("未检测到 API Key，切换至演示模式")
            return ApiResponse(logs=logs, markdown=_demo_content(req.subject, "outline"))

        user_id = getattr(request.state, "user", "") or ""
        actual = req.skill_override if req.skill_override else "research"

        # MCP 预搜索
        mcp_ctx = ""
        if req.mcp_servers:
            mcp_ctx, mcp_logs = _mcp_enhance(req.mcp_servers, req.subject)
            logs.extend(mcp_logs)

        ctx = SkillContext(topic=req.subject, provider_name=provider, model_id=model,
                           custom_params={"depth": 2, "sources": ["web", "semantic_scholar"], "context": (req.context or req.field or "") + mcp_ctx, "request_id": req.request_id},
                           user_id=user_id)
        research_result = get_skill_registry().execute(actual, ctx)
        logs.append("调研完成，正在生成大纲...")

        mgr = get_model_manager()
        llm = mgr.create_llm_client(provider, model, 0.7)
        paper_type = req.paper_type or "研究论文"
        context = req.context or ""
        prompt = f"""基于以下调研内容，为{paper_type}构思框架。
研究主题：{req.subject}
领域：{req.field or '通用'}
额外上下文：{context[:1000] if context else '无'}
调研内容：{research_result.content[:3000] if research_result.content else ''}

请生成：选题价值、论文大纲、创新点、参考文献、写作建议。"""
        resp = llm.invoke([{"role": "user", "content": prompt}])
        content = resp.content if hasattr(resp, "content") else str(resp)
        logs.append("大纲生成完成！")
        from src.api.routers.history import save_report
        save_report("outline", req.subject, content)
        return ApiResponse(logs=logs, markdown=content)
    except Exception as e:
        logs.append(f"❌ 大纲生成出错: {_format_error(e)}")
        return ApiResponse(logs=logs, markdown=f"### ⚠️ 大纲生成失败\n\n**错误**: {_format_error(e)}\n\n请检查服务商配置。")


@router.post("/api/thesis", response_model=ApiResponse)
async def thesis(req: ThesisRequest, request: Request):
    style_map = {
        "Nature标准格式": "academic",
        "ACM/IEEE 双栏通排范式": "ieee",
        "深度研究专著体叙述": "apa",
    }
    style = style_map.get(req.style, req.style)
    logs = ["正在分析章节控制变量与技术深度...", "开始生成学术段落..."]
    try:
        provider, model = resolve_provider_model(req.provider, req.model)

        if not has_api_key(provider):
            logs.append("未检测到 API Key，切换至演示模式")
            return ApiResponse(logs=logs, markdown=_demo_content(req.blockTitle, "thesis"))

        user_id = getattr(request.state, "user", "") or ""
        sections = req.sections or ["abstract", "introduction", "methodology", "experiments", "conclusion"]
        actual = req.skill_override if req.skill_override else "paper_writing"

        # MCP 预搜索
        mcp_ctx = ""
        if req.mcp_servers:
            mcp_ctx, mcp_logs = _mcp_enhance(req.mcp_servers, req.blockTitle)
            logs.extend(mcp_logs)

        combined_context = req.prompt + ("\n" + req.context if req.context else "") + ("\n" + mcp_ctx if mcp_ctx else "")
        content, _steps = await _execute_skill_with_timeout(actual, req.blockTitle, provider, model, {
            "paper_type": req.paper_type or "research",
            "style": style,
            "length": req.length or "medium",
            "sections": sections,
            "context": combined_context,
            "request_id": req.request_id,
        }, timeout=600, user_id=user_id)
        logs.append("学术段落生成完成！")
        from src.api.routers.history import save_report
        save_report("thesis", req.blockTitle, content)
        return ApiResponse(logs=logs, markdown=content)
    except Exception as e:
        logs.append(f"❌ 学术段落生成出错: {_format_error(e)}")
        return ApiResponse(logs=logs, markdown=f"### ⚠️ 学术段落生成失败\n\n**错误**: {_format_error(e)}\n\n请检查服务商配置。")


@router.post("/api/literature-review", response_model=ApiResponse)
async def literature_review(req: ReviewRequest, request: Request):
    logs = [f"开始扫描关于 [{req.keyword}] 的学术文献..."]
    try:
        provider, model = resolve_provider_model(req.provider, req.model)

        if not has_api_key(provider):
            logs.append("未检测到 API Key，切换至演示模式")
            return ApiResponse(logs=logs, markdown=_demo_content(req.keyword, "literature-review"))

        user_id = getattr(request.state, "user", "") or ""
        actual = req.skill_override if req.skill_override else "survey_writing"

        # MCP 预搜索
        mcp_ctx = ""
        if req.mcp_servers:
            mcp_ctx, mcp_logs = _mcp_enhance(req.mcp_servers, req.keyword)
            logs.extend(mcp_logs)

        combined_context = (req.context or "") + ("\n" + mcp_ctx if mcp_ctx else "")
        content, _steps = await _execute_skill_with_timeout(actual, req.keyword, provider, model, {
            "scope": req.scope or "focused",
            "taxonomy": req.taxonomy,
            "comparisons": req.comparisons,
            "context": combined_context,
            "request_id": req.request_id,
        }, timeout=600, user_id=user_id)
        logs.append("文献综述合成完成！")
        from src.api.routers.history import save_report
        save_report("review", req.keyword, content)
        return ApiResponse(logs=logs, markdown=content)
    except Exception as e:
        logs.append(f"❌ 文献综述生成出错: {_format_error(e)}")
        return ApiResponse(logs=logs, markdown=f"### ⚠️ 文献综述生成失败\n\n**错误**: {_format_error(e)}\n\n请检查服务商配置。")
