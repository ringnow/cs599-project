"""POST /api/report, /api/outline, /api/thesis, /api/literature-review — Generation endpoints."""
import logging
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

logger = logging.getLogger("cs599.mcp")


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
        return "", [], []
    logs = []
    mcp_search_results = []
    logger.info("🔌 MCP 增强搜索启动: servers=%s, topic=%s", mcp_servers, topic[:60])
    try:
        from src.mcp.manager import get_mcp_manager
        mgr = get_mcp_manager()
        snippets = []

        for srv_name in mcp_servers:
            # 自动初始化：如果预设存在但未添加，自动添加并启动
            try:
                from src.mcp.manager import BUILTIN_MCP_PRESETS
                if not mgr.is_server_enabled(srv_name):
                    if srv_name in BUILTIN_MCP_PRESETS:
                        preset = BUILTIN_MCP_PRESETS[srv_name]
                        msg = f"⚙️ MCP {srv_name} 首次使用，自动注册..."
                        logs.append(f"  {msg}")
                        logger.info("MCP %s", msg)
                        ok, msg2 = mgr.add_from_preset(srv_name)
                        logs.append(f"  ⚙️   → 注册: {msg2}")
                        logger.info("MCP %s → 注册: %s", srv_name, msg2)
                        if preset.server_type == "stdio":
                            ok3, msg3 = mgr.start_stdio_server(srv_name)
                            logs.append(f"  ⚙️   → 启动: {msg3}")
                            logger.info("MCP %s → 启动: %s", srv_name, msg3)
                    else:
                        logs.append(f"  ⏭️ MCP {srv_name} 预设不存在，跳过")
                        logger.warning("MCP %s 预设不存在，跳过", srv_name)
                        continue
                elif mgr.get_server(srv_name) and \
                     mgr.get_server(srv_name).server_type == "stdio" and \
                     not mgr.is_stdio_running(srv_name):
                    ok3, msg3 = mgr.start_stdio_server(srv_name)
                    logs.append(f"  🔄 MCP {srv_name} 重启: {msg3}")
                    logger.info("MCP %s 重启: %s", srv_name, msg3)
            except Exception as e:
                logs.append(f"  ⚠️ MCP {srv_name} 初始化异常: {str(e)[:100]}")
                logger.warning("MCP %s 初始化异常: %s", srv_name, e)
                continue

            logs.append(f"🔌 正在调用 MCP 服务器: {srv_name}")
            logger.info("🔌 正在调用 MCP 服务器: %s", srv_name)

            try:
                if "fetch" in srv_name:
                    # arxiv 需要英文关键词，中文主题先用 LLM 生成多个短关键词
                    arxiv_queries = [topic]
                    if any('\u4e00' <= c <= '\u9fff' for c in topic):
                        try:
                            from src.models.manager import get_model_manager
                            from src.api.dependencies import resolve_provider_model
                            p, m = resolve_provider_model()
                            llm = get_model_manager().create_llm_client(p, m, 0.1)
                            resp = llm.invoke([{"role": "user", "content":
                                f"将以下研究主题提炼为3个简短的英文关键词组合，每行一个，"
                                f"每行不超过6个词，用于搜索学术论文：{topic}"}])
                            lines = [l.strip() for l in resp.content.strip().split("\n") if l.strip()] if hasattr(resp, "content") else [topic]
                            arxiv_queries = [l for l in lines if len(l) > 5][:3]
                            logger.info("MCP arxiv 关键词: %r", arxiv_queries)
                            logs.append(f"  🔍 arxiv 关键词: {arxiv_queries}")
                        except Exception as e:
                            logs.append(f"  ⚠️ arxiv 关键词生成失败: {type(e).__name__}: {str(e)[:100]}")
                            logger.warning("arxiv 关键词生成失败: %s", e)
                    # 用多个关键词分别搜索，合并结果去重
                    import urllib.parse as _up
                    import time as _time
                    seen_titles = set()
                    for aq_idx, aq in enumerate(arxiv_queries[:2]):  # 最多 2 个关键词，避免限流
                        # arxiv 限流：关键词之间至少间隔 5 秒
                        if aq_idx > 0:
                            _time.sleep(5)
                        # ★ R7: 跳过含中文的关键词（arxiv 不支持）
                        if any('\u4e00' <= c <= '\u9fff' for c in aq):
                            logs.append(f"  ⏭️ 跳过含中文关键词: {aq}")
                            continue
                        try:
                            encoded = _up.quote(aq, safe="")
                            fetch_url = f"https://export.arxiv.org/api/query?search_query=all:{encoded}&max_results=3&sortBy=relevance&sortOrder=descending"
                            r = mgr.call_tool(srv_name, "fetch", {"url": fetch_url})
                            if not r or "error" in r:
                                err_msg = r.get("error", "unknown") if r else "no response"
                                logs.append(f"  ⚠️ MCP fetch arxiv error ({aq}): {err_msg}")
                                logger.warning("MCP fetch arxiv error (%s): %s", aq, err_msg)
                                continue
                            papers = _parse_arxiv_xml(r)
                            for p in papers:
                                title = p.split(".")[0] if "." in p else p[:50]
                                if title not in seen_titles:
                                    seen_titles.add(title)
                                    snippets.append(f"[arxiv] {p}")
                            # 结构化数据
                            structured = _parse_arxiv_structured(r)
                            for s in structured:
                                if s["title"] not in seen_titles:
                                    seen_titles.add(s["title"])
                                    mcp_search_results.append(s)
                        except Exception as e:
                            logs.append(f"  ⚠️ MCP fetch arxiv 异常 ({aq}): {type(e).__name__}: {str(e)[:100]}")
                            logger.warning("MCP fetch arxiv 异常 (%s): %s", aq, e)
                    logs.append(f"  ✅ MCP fetch → arxiv: {len(seen_titles)} 篇论文 (去重)")
                    logger.info("MCP fetch → arxiv: %d 篇论文 (去重, queries=%d)", len(seen_titles), len(arxiv_queries))

                elif "filesystem" in srv_name:
                    import os as _os
                    _project_root = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.dirname(__file__))))
                    fs_path = _os.path.join(_os.path.abspath(_project_root), "research_outputs")
                    # ★ R4: 更新 allowed_dir 并重启 server 使配置生效
                    mgr.update(srv_name, url=fs_path)
                    mgr.stop_stdio_server(srv_name)
                    mgr.start_stdio_server(srv_name)
                    # ★ R8: 参数名兼容新版（directory）和旧版（path）
                    r = mgr.call_tool(srv_name, "list_directory", {"directory": fs_path, "path": fs_path})
                    if not r or "error" in r:
                        err_msg = r.get("error", "unknown") if r else "no response"
                        logs.append(f"  ⚠️ MCP filesystem error: {err_msg}")
                        logger.warning("MCP filesystem error: %s", err_msg)
                    else:
                        raw = r.get("result", r.get("raw", ""))
                        items = raw if isinstance(raw, list) else []
                        matching = [item for item in items if isinstance(item, str) and topic.lower() in item.lower()]
                        for item in matching[:5]:
                            snippets.append(f"[本地文件] {item}")
                        logs.append(f"  ✅ MCP filesystem: 扫描到 {len(matching)} 个相关文件")
                        logger.info("MCP filesystem: 扫描到 %d 个相关文件", len(matching))

                elif "memory" in srv_name:
                    r = mgr.call_tool(srv_name, "search_nodes", {"query": topic})
                    if not r or "error" in r:
                        err_msg = r.get("error", "unknown") if r else "no response"
                        logs.append(f"  ⚠️ MCP memory error: {err_msg}")
                        logger.warning("MCP memory error: %s", err_msg)
                    else:
                        raw = r.get("result", r.get("raw", ""))
                        if isinstance(raw, dict) and raw.get("entities"):
                            for ent in raw["entities"][:3]:
                                name = ent.get("name", "")
                                obs = "; ".join(ent.get("observations", [])[:2])
                                snippets.append(f"[记忆] {name}: {obs[:200]}")
                        logs.append(f"  ✅ MCP memory: 查询知识图谱完成")
                        logger.info("MCP memory: 查询知识图谱完成")

                elif "sequential" in srv_name:
                    # ★ R5: 补齐必填参数
                    r = mgr.call_tool(srv_name, "sequentialthinking", {
                        "thought": f"Research topic: {topic}. Break down into sub-questions.",
                        "thoughtNumber": 1,
                        "totalThoughts": 3,
                        "nextThoughtNeeded": True,
                    })
                    if not r or "error" in r:
                        err_msg = r.get("error", "unknown") if r else "no response"
                        logs.append(f"  ⚠️ MCP sequential-thinking error: {err_msg}")
                        logger.warning("MCP sequential-thinking error: %s", err_msg)
                    else:
                        raw = r.get("result", r.get("raw", ""))
                        if isinstance(raw, dict) and raw.get("thought"):
                            snippets.append(f"[推理] {raw['thought'][:300]}")
                        logs.append(f"  ✅ MCP sequential-thinking: 推理完成")
                        logger.info("MCP sequential-thinking: 推理完成")

                else:
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
                logger.warning("MCP %s 调用异常: %s", srv_name, e)

        context = "\nMCP搜索结果：\n" + "\n".join(snippets[:10]) if snippets else ""
        return context, logs, mcp_search_results
    except Exception as e:
        logger.warning("MCP 增强搜索异常: %s", e)
        return "", [f"❌ MCP 管理器错误: {str(e)[:100]}"], []


def _parse_arxiv_xml(raw: Any) -> List[str]:
    """解析 arxiv Atom XML → 人类可读的引用文本。"""
    try:
        import xml.etree.ElementTree as ET
        result = raw.get("result", "") if isinstance(raw, dict) else str(raw)
        root = ET.fromstring(result)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        papers = []
        for entry in root.findall("atom:entry", ns):
            title = entry.findtext("atom:title", "", ns).strip().replace("\n", " ").replace("  ", " ")
            link = entry.findtext("atom:id", "", ns)
            published = entry.findtext("atom:published", "", ns)[:4]
            authors = []
            for author in entry.findall("atom:author", ns):
                name = author.findtext("atom:name", "", ns)
                if name:
                    authors.append(name.strip())
            author_str = ", ".join(authors[:3])
            if len(authors) > 3:
                author_str += " et al."
            papers.append(f"{author_str} ({published}). \"{title}.\" arXiv preprint. {link}")
        return papers
    except Exception:
        return []


def _parse_arxiv_structured(raw: Any) -> List[dict]:
    """解析 arxiv Atom XML → SearchResult 结构体（用于论文评估管道）。"""
    try:
        import xml.etree.ElementTree as ET
        result = raw.get("result", "") if isinstance(raw, dict) else str(raw)
        root = ET.fromstring(result)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        papers = []
        for entry in root.findall("atom:entry", ns):
            title = entry.findtext("atom:title", "", ns).strip().replace("\n", " ").replace("  ", " ")
            summary = entry.findtext("atom:summary", "", ns).strip()[:500].replace("\n", " ")
            link = entry.findtext("atom:id", "", ns)
            published = entry.findtext("atom:published", "", ns)[:4]
            authors = []
            for author in entry.findall("atom:author", ns):
                name = author.findtext("atom:name", "", ns)
                if name:
                    authors.append(name.strip())
            papers.append({
                "title": title,
                "url": link,
                "snippet": summary,
                "source": "arxiv",
                "year": int(published) if published.isdigit() else 0,
                "authors": authors,
            })
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
            mcp_ctx, mcp_logs, mcp_arxiv = _mcp_enhance(req.mcp_servers, req.subject)
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
            "mcp_search_results": mcp_arxiv,
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
            mcp_ctx, mcp_logs, mcp_arxiv = _mcp_enhance(req.mcp_servers, req.subject)
            logs.extend(mcp_logs)
            if mcp_arxiv:
                req.mcp_search_results = mcp_arxiv

        ctx = SkillContext(topic=req.subject, provider_name=provider, model_id=model,
                           custom_params={"depth": 2, "sources": ["web", "semantic_scholar"], "context": (req.context or req.field or "") + mcp_ctx, "request_id": req.request_id, "mcp_search_results": getattr(req, "mcp_search_results", [])},
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
            mcp_ctx, mcp_logs, mcp_arxiv = _mcp_enhance(req.mcp_servers, req.blockTitle)
            logs.extend(mcp_logs)

        combined_context = req.prompt + ("\n" + req.context if req.context else "") + ("\n" + mcp_ctx if mcp_ctx else "")
        content, _steps = await _execute_skill_with_timeout(actual, req.blockTitle, provider, model, {
            "paper_type": req.paper_type or "research",
            "style": style,
            "length": req.length or "medium",
            "sections": sections,
            "context": combined_context,
            "mcp_search_results": mcp_arxiv,
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
            mcp_ctx, mcp_logs, mcp_arxiv = _mcp_enhance(req.mcp_servers, req.keyword)
            logs.extend(mcp_logs)

        combined_context = (req.context or "") + ("\n" + mcp_ctx if mcp_ctx else "")
        content, _steps = await _execute_skill_with_timeout(actual, req.keyword, provider, model, {
            "scope": req.scope or "focused",
            "taxonomy": req.taxonomy,
            "comparisons": req.comparisons,
            "context": combined_context,
            "mcp_search_results": mcp_arxiv,
            "request_id": req.request_id,
        }, timeout=600, user_id=user_id)
        logs.append("文献综述合成完成！")
        from src.api.routers.history import save_report
        save_report("review", req.keyword, content)
        return ApiResponse(logs=logs, markdown=content)
    except Exception as e:
        logs.append(f"❌ 文献综述生成出错: {_format_error(e)}")
        return ApiResponse(logs=logs, markdown=f"### ⚠️ 文献综述生成失败\n\n**错误**: {_format_error(e)}\n\n请检查服务商配置。")
