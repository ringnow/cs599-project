"""POST /api/assistant — Smart assistant with intent analysis."""
import json, re
from datetime import datetime

from fastapi import APIRouter
from src.models.manager import get_model_manager
from src.models.key_store import get_key_store
from src.skills.registry import get_skill_registry
from src.skills.base import SkillContext
from src.api.schemas import AssistantRequest, ApiResponse

router = APIRouter()


def _provider_model(req_provider: str = "", req_model: str = ""):
    """Get provider & model — prefer request params, then configured default."""
    mgr = get_model_manager()
    if req_provider:
        p = mgr.get_provider(req_provider)
        if p:
            return p.config.name, req_model or p.config.default_model or "deepseek-chat"
    default = mgr.default_provider
    if default:
        cfg = next((c for c in mgr.list_providers() if c.name == default), None)
        if cfg:
            return cfg.name, cfg.default_model or "deepseek-chat"
    providers = mgr.list_providers()
    if providers:
        p = providers[0]
        return p.name, p.default_model or "deepseek-chat"
    return "deepseek", "deepseek-chat"


def _has_api_key(provider_name: str) -> bool:
    """Check if provider has a valid API key configured."""
    ks = get_key_store()
    key = ks.get_key(provider_name)
    return bool(key and key.strip() and key.strip() != "no-key" and key.strip() != "YOUR_API_KEY")


def _demo_content(topic: str) -> str:
    """Return demo content when no API key is configured."""
    return f"""### 演示模式 — 未配置 API Key

当前正在处理：**{topic}**

---

#### 1. 前沿挑战与研究现状

在计算科学与人工智能的交叉领域，本主题的研究正在经历范式转变。基于深度表示学习和自适应对齐的模型能够解决长上下文建模、计算稳定性约束与跨域零样本迁移等核心痛点。

#### 2. 核心学术架构设计

- **感知对齐层 (Perceptual Alignment Layer)**: 对多源异构输入进行归一化处理
- **博弈演化模块 (Evolutionary Game Module)**: 通过模拟自适应网络转移函数，实现分布式智能体间的局部纳什对齐
- **可解释性自回归模型 (Explainable Auto-regressive Logic)**: 增加可解释注意力张量的权重分布，帮助追踪决策归因

#### 3. 领域经典参考文献

1. **Zhang, Y., & Wang, H. (2025).** "Scalable Deep Autoencoders for Multi-agent Coordination and Federated Topologies." *Journal of Machine Learning Research (JMLR)*, vol. 26, pp. 112–134.
2. **Li, S., et al. (2025).** "Decentralized Optimal Control with Deep Implicit Layers." *IEEE Transactions on Pattern Analysis and Machine Intelligence (TPAMI)*, vol. 47, no. 3, pp. 1024–1039.

---

> 提示：请在「服务商管理」中配置有效的 API Key 以启用实时的 AI 学术大模型生成。
> 支持的提供商：DeepSeek、OpenAI、Anthropic、硅基流动、OpenRouter 等。
"""


@router.post("/api/assistant", response_model=ApiResponse)
def assistant(req: AssistantRequest):
    logs = ["正在初始化 CS599 智能助手计算流..."]
    try:
        mgr = get_model_manager()
        provider, model = _provider_model(req.provider, req.model)

        # Check API key before any LLM calls
        if not _has_api_key(provider):
            logs.append("未检测到 API Key，切换至演示模式")
            return ApiResponse(logs=logs, markdown=_demo_content(req.prompt))

        # Intent analysis
        logs.append("正在分析语义意图与路由决策...")
        llm = mgr.create_llm_client(provider, model, 0.3)
        ctx_block = f"\n上下文：{req.context}" if req.context else ""
        prompt = f"""分析用户需求，判断工具。可用工具：research/survey_writing/paper_writing/crew/chat。
用户输入：{req.prompt}{ctx_block}
只输出JSON：{{"tool": "...", "topic": "...", "reason": "..."}}"""
        resp = llm.invoke([{"role": "user", "content": prompt}])
        raw = resp.content if hasattr(resp, "content") else str(resp)
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        decision = json.loads(m.group()) if m else {"tool": "chat", "topic": req.prompt}
        tool = decision.get("tool", "chat")
        topic = decision.get("topic", req.prompt)
        logs.append(f"意图识别: {tool} | 主题: {topic[:50]}")

        # Tool execution — let the skill handle its own search internally
        if tool in ("research", "survey_writing", "paper_writing", "crew"):
            logs.append("正在搜索学术信息...")
            context = req.context or ""
            logs.append("已传递上下文，开始执行技能模块...")

        logs.append(f"执行 {tool} 模块...")

        if tool == "chat":
            chat_prompt = f"用户：{req.prompt}\n{ctx_block}\n请详细回答。"
            resp = llm.invoke([{"role": "user", "content": chat_prompt}])
            content = resp.content if hasattr(resp, "content") else str(resp)
            logs.append("生成完成！")
            from src.api.routers.history import save_report
            save_report("assistant", req.prompt, content)
            return ApiResponse(logs=logs, markdown=content)

        if tool == "crew":
            from src.crew.crew import Crew
            crew = Crew(provider_name=provider, model_id=model)
            result = crew.run_sequential(topic, "report", 1)
            content = result.get("document", "")
            logs.append("多智能体协作完成！")
            from src.api.routers.history import save_report
            save_report("assistant_crew", topic, content)
            return ApiResponse(logs=logs, markdown=content)

        skill_map = {"research": "research", "survey_writing": "survey_writing",
                     "paper_writing": "paper_writing"}
        ctx = SkillContext(topic=topic, provider_name=provider, model_id=model,
                           custom_params={"depth": 2, "sources": ["web", "semantic_scholar"],
                                          "context": context or "",
                                          "request_id": req.request_id})
        sr = get_skill_registry().execute(skill_map.get(tool, "research"), ctx)
        logs.append("生成完成！")
        if sr.success:
            from src.api.routers.history import save_report
            save_report("assistant_" + tool, topic, sr.content)
            return ApiResponse(logs=logs, markdown=sr.content)
        else:
            logs.append(f"❌ 技能执行失败: {sr.error}")
            return ApiResponse(logs=logs, markdown=f"### ⚠️ 技能执行失败\n\n**错误信息**：{sr.error}\n\n请检查服务商配置或稍后重试。")

    except Exception as e:
        err_name = type(e).__name__
        err_msg = str(e)
        logs.append(f"❌ 执行出错 [{err_name}]: {err_msg[:200]}")
        logs.append("💡 请检查服务商 API Key 配置，或在服务商管理中确认供应商状态。")
        return ApiResponse(
            logs=logs,
            markdown=f"### ⚠️ 智能助手执行出错\n\n**错误类型**：`{err_name}`\n\n**详细信息**：\n```\n{err_msg[:500]}\n```\n\n#### 排查建议\n1. 确认已在「服务商管理」中配置了有效的 API Key\n2. 检查所选供应商和模型是否正确\n3. 确认后端网络可以访问模型 API 端点\n4. 查看上方日志控制台获取更详细的错误信息",
        )
