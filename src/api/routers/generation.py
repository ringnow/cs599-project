"""POST /api/report, /api/outline, /api/thesis, /api/literature-review — Generation endpoints."""
from datetime import datetime
from typing import List

from fastapi import APIRouter
from src.models.manager import get_model_manager
from src.models.key_store import get_key_store
from src.skills.registry import get_skill_registry
from src.skills.base import SkillContext
from src.api.schemas import ReportRequest, OutlineRequest, ThesisRequest, ReviewRequest, ApiResponse
from src.api.dependencies import resolve_provider_model, has_api_key
import asyncio
import concurrent.futures

router = APIRouter()


def _mcp_context(mcp_servers: List[str], topic: str) -> tuple:
    """Run MCP pre-search and return context snippet + logs."""
    if not mcp_servers:
        return "", []
    logs = []
    try:
        from src.mcp.manager import get_mcp_manager
        mgr = get_mcp_manager()
        snippets = []
        for srv in mcp_servers:
            logs.append(f"🔌 正在调用 MCP 服务器: {srv}")
            try:
                r = mgr.call_tool(srv, "search", {"query": topic, "max_results": 3})
                if "error" not in r:
                    parsed = r.get("result", r.get("raw", []))
                    items = parsed.get("results", parsed) if isinstance(parsed, dict) else (parsed if isinstance(parsed, list) else [])
                    count = 0
                    for item in (items if isinstance(items, list) else [items]):
                        if isinstance(item, dict):
                            snippets.append(f"- {item.get('title','')}: {item.get('content',item.get('snippet',''))[:200]}")
                            count += 1
                    logs.append(f"  ✅ MCP {srv} 返回 {count} 条结果")
                else:
                    logs.append(f"  ⚠️ MCP {srv} 调用错误: {r['error'][:100]}")
            except Exception as e:
                logs.append(f"  ❌ MCP {srv} 异常: {str(e)[:100]}")
                pass
        context = "\nMCP搜索结果：\n" + "\n".join(snippets[:5]) if snippets else ""
        return context, logs
    except Exception as e:
        return "", [f"❌ MCP 管理器错误: {str(e)[:100]}"]


def _execute_skill(actual: str, topic: str, provider: str, model: str, params: dict):
    """Execute a skill and return markdown string + steps."""
    ctx = SkillContext(topic=topic, provider_name=provider, model_id=model, custom_params=params)
    sr = get_skill_registry().execute(actual, ctx)
    if sr.success:
        return sr.content, sr.steps
    return f"技能执行失败: {sr.error}", sr.steps


async def _execute_skill_with_timeout(actual: str, topic: str, provider: str, model: str, params: dict, timeout: int = 240):
    """Execute a skill with a timeout to prevent hanging.

    Runs the blocking skill code in a thread pool so the async event loop
    is NOT blocked during long-running research tasks.
    """
    loop = asyncio.get_event_loop()
    try:
        return await asyncio.wait_for(
            loop.run_in_executor(None, _execute_skill, actual, topic, provider, model, params),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        return f"技能执行超时（{timeout}秒）。请检查服务商配置和网络连接。"


def _demo_content(topic: str, task_type: str) -> str:
    """Return demo content when no API key is configured."""
    return f"""### 演示模式 — 未配置 API Key

当前正在处理主题：**{topic}**

---

#### 1. 前沿挑战与研究现状

在计算科学与人工智能的交叉领域，**{topic}** 的研究正在经历范式转变。基于深度表示学习和自适应对齐的模型能够解决长上下文建模、计算稳定性约束与跨域零样本迁移等核心痛点。

#### 2. 核心学术架构设计

- **感知对齐层 (Perceptual Alignment Layer)**: 对多源异构输入进行归一化处理
- **博弈演化模块 (Evolutionary Game Module)**: 通过模拟自适应网络转移函数，实现分布式智能体间的局部纳什对齐
- **可解释性自回归模型 (Explainable Auto-regressive Logic)**: 增加可解释注意力张量的权重分布，帮助追踪决策归因

#### 3. 领域经典参考文献

1. **Zhang, Y., & Wang, H. (2025).** "Scalable Deep Autoencoders for Multi-agent Coordination and Federated Topologies." *Journal of Machine Learning Research (JMLR)*, vol. 26, pp. 112-134.
2. **Li, S., et al. (2025).** "Decentralized Optimal Control with Deep Implicit Layers." *IEEE Transactions on Pattern Analysis and Machine Intelligence (TPAMI)*, vol. 47, no. 3, pp. 1024-1039.

---

> 提示：请在「服务商管理」中配置有效的 API Key 以启用实时的 AI 学术大模型生成。
> 支持的提供商：DeepSeek、OpenAI、Anthropic、硅基流动、OpenRouter 等。
"""


@router.post("/api/report", response_model=ApiResponse)
async def report(req: ReportRequest):
    logs = ["初始化学术报告生成器...", f"分析研究领域: {req.field or '通用'}", f"生成深度: {req.depth}"]
    try:
        depth_map = {"基础": 1, "详细": 3, "专家": 5}
        provider, model = _provider_model(req.provider, req.model)

        if not _has_api_key(provider):
            logs.append("未检测到 API Key，切换至演示模式")
            return ApiResponse(logs=logs, markdown=_demo_content(req.subject, "report"))

        mcp_ctx = ""
        if req.mcp_servers:
            mcp_ctx, mcp_logs = _mcp_context(req.mcp_servers, req.subject)
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
        })
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
        logs.append(f"❌ 报告生成出错: {str(e)[:200]}")
        return ApiResponse(logs=logs, markdown=f"### ⚠️ 报告生成失败\n\n**错误**: {str(e)[:500]}\n\n请检查服务商配置。")


@router.post("/api/outline", response_model=ApiResponse)
async def outline(req: OutlineRequest):
    logs = ["正在调研相关领域...", "正在进行论文构思..."]
    try:
        provider, model = resolve_provider_model(req.provider, req.model)

        if not has_api_key(provider):
            logs.append("未检测到 API Key，切换至演示模式")
            return ApiResponse(logs=logs, markdown=_demo_content(req.subject, "outline"))

        actual = req.skill_override if req.skill_override else "research"
        ctx = SkillContext(topic=req.subject, provider_name=provider, model_id=model,
                           custom_params={"depth": 2, "sources": ["web", "semantic_scholar"], "context": req.context or req.field, "request_id": req.request_id})
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
        logs.append(f"❌ 大纲生成出错: {str(e)[:200]}")
        return ApiResponse(logs=logs, markdown=f"### ⚠️ 大纲生成失败\n\n**错误**: {str(e)[:500]}\n\n请检查服务商配置。")


@router.post("/api/thesis", response_model=ApiResponse)
async def thesis(req: ThesisRequest):
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

        sections = req.sections or ["abstract", "introduction", "methodology", "experiments", "conclusion"]
        actual = req.skill_override if req.skill_override else "paper_writing"
        content, _steps = await _execute_skill_with_timeout(actual, req.blockTitle, provider, model, {
            "paper_type": req.paper_type or "research",
            "style": style,
            "length": req.length or "medium",
            "sections": sections,
            "context": req.prompt + ("\n" + req.context if req.context else ""),
            "request_id": req.request_id,
        })
        logs.append("学术段落生成完成！")
        from src.api.routers.history import save_report
        save_report("thesis", req.blockTitle, content)
        return ApiResponse(logs=logs, markdown=content)
    except Exception as e:
        logs.append(f"❌ 学术段落生成出错: {str(e)[:200]}")
        return ApiResponse(logs=logs, markdown=f"### ⚠️ 学术段落生成失败\n\n**错误**: {str(e)[:500]}\n\n请检查服务商配置。")


@router.post("/api/literature-review", response_model=ApiResponse)
async def literature_review(req: ReviewRequest):
    logs = [f"开始扫描关于 [{req.keyword}] 的学术文献..."]
    try:
        provider, model = resolve_provider_model(req.provider, req.model)

        if not has_api_key(provider):
            logs.append("未检测到 API Key，切换至演示模式")
            return ApiResponse(logs=logs, markdown=_demo_content(req.keyword, "literature-review"))

        actual = req.skill_override if req.skill_override else "survey_writing"
        content, _steps = await _execute_skill_with_timeout(actual, req.keyword, provider, model, {
            "scope": req.scope or "focused",
            "taxonomy": req.taxonomy,
            "comparisons": req.comparisons,
            "context": req.context or "",
            "request_id": req.request_id,
        })
        logs.append("文献综述合成完成！")
        from src.api.routers.history import save_report
        save_report("review", req.keyword, content)
        return ApiResponse(logs=logs, markdown=content)
    except Exception as e:
        logs.append(f"❌ 文献综述生成出错: {str(e)[:200]}")
        return ApiResponse(logs=logs, markdown=f"### ⚠️ 文献综述生成失败\n\n**错误**: {str(e)[:500]}\n\n请检查服务商配置。")
