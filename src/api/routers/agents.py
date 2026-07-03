"""POST /api/agents-collaborate — Multi-agent collaboration."""
from datetime import datetime

from fastapi import APIRouter, Request
from src.models.manager import get_model_manager
from src.api.schemas import AgentCollaborateRequest, ApiResponse
from src.api.dependencies import resolve_provider_model, has_api_key

router = APIRouter()


def _demo_collaboration(topic: str):
    """Return demo collaboration data when no API key is configured."""
    exchange = [
        {
            "agent": "搜索专家 (Search Expert)",
            "message": f"我已接入高引数据库，关于「{topic}」，已检索到ICML 2025、CVPR 2025的最新预印本32篇。关键文献主要集中在异构拓扑网络下的分布式收敛问题，已成功提炼出两个主流技术路线：全连通异步网络与星型有向对齐环。"
        },
        {
            "agent": "分析助手 (Analysis Assistant)",
            "message": "根据搜索专家提供的信息，我对这两种模型进行了复杂度分析。异步全连通网络虽然收敛上限极高，但通信开销达到对数立方级 O(N^3 log N)；而有向对齐环在牺牲5%收敛精度的同时，将每次迭代的吞吐代价平抑到了线性级 O(N)。因此在可拓展架构中，首推后一方案。"
        },
        {
            "agent": "写作专家 (Writing Expert)",
            "message": "收到。我将整理分析助手给出的复杂度比对结果。综述引言及理论设计部分，我们可以以定理（Theorem 1.1）的形式严格列出不同拓扑结构的流形流收敛界限，并以 LaTeX 数式和图表对比呈现，生成一份完整的学术方案草案。"
        }
    ]
    markdown = f"""### **多智能体协同输出：关于《{topic}》的可行性方案**

本方案由 **搜索专家**、**分析助手** 与 **写作专家** 自主完成多轮博弈交流得出：

#### **1. 拓扑复杂度对比矩阵**
| 拓扑结构 | 关键代表发布 | 核心优势 | 瓶颈 | 通信时空复杂度 |
| :--- | :--- | :--- | :--- | :--- |
| **异步全连通 (Fully Connected)** | Zhang et al. (ICML '25) | 高稳定性、全局收敛 | 极端通信损耗 | O(N^3 log N) |
| **有向对齐环 (Directed Alignment)** | CS599 (NeurIPS '25) | 有限开销、线性拓展 | 存在收敛时滞 | O(N) |

#### **2. 协同成果总结**
在分布式系统中，推荐采用**有向自适应对齐环**架构，由于各计算智能体本地只需存储与其相邻的拓扑状态矢量。系统整体可用性得到了质的飞跃。

#### **3. 文献引用目录**
- *Ref-A*: "Asynchronous Multi-Agent Convergence Topologies." *ICML*, 2025.
- *Ref-B*: "Linear Complexity in Directed Consensus Systems." *NeurIPS*, 2025.

---

> 提示：请在「服务商管理」中配置有效的 API Key 以启用实时的多智能体协作功能。
"""
    return exchange, markdown


@router.post("/api/agents-collaborate", response_model=ApiResponse)
def agents_collaborate(req: AgentCollaborateRequest, request: Request):
    try:
        provider, model = resolve_provider_model(req.provider, req.model)
        logs = [
            "正在启动多智能体协作网络...",
            f"任务主题: {req.topic[:60]}",
            f"文档类型: {req.doc_type}, 迭代轮数: {req.iterations}",
        ]

        # MCP 预搜索
        mcp_ctx = ""
        mcp_arxiv = []
        if req.mcp_servers:
            from src.api.routers.generation import _mcp_enhance
            mcp_ctx, mcp_logs, mcp_arxiv = _mcp_enhance(req.mcp_servers, req.topic)
            logs.extend(mcp_logs)

        # Check API key before any LLM calls
        if not has_api_key(provider):
            logs.append("未检测到 API Key，切换至演示模式")
            exchange, markdown = _demo_collaboration(req.topic)
            return ApiResponse(logs=logs, markdown=markdown, exchange=exchange)

        # If skill_override is set, use skill instead of Crew
        if req.skill_override:
            logs.append(f"🛠️ 使用指定技能: {req.skill_override}")
            from src.skills.registry import get_skill_registry
            from src.skills.base import SkillContext
            ctx = SkillContext(
                topic=req.topic,
                provider_name=provider,
                model_id=model,
                custom_params={
                    "depth": 2,
                    "sources": ["web", "semantic_scholar"],
                    "context": req.context or "",
                    "mcp_search_results": mcp_arxiv,
                    "request_id": req.request_id,
                },
                user_id=getattr(request.state, "user", "") or "",
            )
            sr = get_skill_registry().execute(req.skill_override, ctx)
            if sr.success:
                logs.append("技能执行完成！")
                from src.api.routers.history import save_report
                save_report("agents", req.topic, sr.content)
                return ApiResponse(logs=logs, markdown=sr.content)
            else:
                logs.append(f"❌ 技能执行失败: {sr.error}")
                return ApiResponse(logs=logs, markdown=f"### ⚠️ 技能执行失败\n\n**错误**: {sr.error}")

        from src.crew.crew import Crew
        crew = Crew(provider_name=provider, model_id=model)
        result = crew.run_sequential(req.topic, doc_type=req.doc_type, max_iterations=req.iterations, context=req.context or "")

        # Build exchange from workflow log (from result dict)
        exchange = []
        workflow_log = result.get("workflow_log", [])
        for entry in workflow_log:
            agent_map = {
                "researcher": "搜索专家 (Search Expert)",
                "critic": "分析助手 (Analysis Assistant)",
                "writer": "写作专家 (Writing Expert)",
            }
            agent_name = entry.get("agent", "")
            agent_label = agent_map.get(agent_name, agent_name)
            message = entry.get("message", "")
            if message:
                exchange.append({"agent": agent_label, "message": message})

        document = result.get("document", "")
        logs.append("多智能体协作完成！")
        from src.api.routers.history import save_report
        save_report("agents", req.topic, document)

        return ApiResponse(
            logs=logs,
            markdown=document,
            exchange=exchange if exchange else None,
        )
    except Exception as e:
        logs = [
            "正在启动多智能体协作网络...",
            f"任务主题: {req.topic[:60]}",
            f"❌ 多智能体协作出错: {str(e)[:200]}",
        ]
        return ApiResponse(
            logs=logs,
            markdown=f"### ⚠️ 多智能体协作失败\n\n**错误**: {str(e)[:500]}\n\n请检查服务商配置后重试。",
        )
