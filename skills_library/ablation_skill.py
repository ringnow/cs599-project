"""消融实验矩阵拟合检测 Skill — 识别数据点中对于消融曲线突变存在异常的特征噪音。"""
import json
import time
from typing import Dict, Any, List

from src.skills.base import BaseSkill, SkillResult, SkillContext
from src.models.manager import get_model_manager


class AblationStudySkill(BaseSkill):
    """Ablation study analysis — detect anomalous features causing mutation in ablation curves."""

    name = "ablation_study"
    display_name = "消融实验矩阵拟合检测"
    description = "识别数据点中对于消融曲线突变存在异常的特征噪音。对消融实验数据进行矩阵拟合分析，检测异常特征点并生成可视化报告。"
    version = "1.0.0"
    author = "CS599 Agent"
    tags = ["分析", "消融实验", "数据挖掘"]

    parameters_schema = {
        "topic": {"type": "string", "description": "消融实验分析主题", "required": True},
    }

    def execute(self, context: SkillContext) -> SkillResult:
        topic = context.topic
        steps = []
        _start = time.time()

        try:
            manager = get_model_manager()
            llm = manager.create_llm_client(
                context.provider_name, context.model_id, context.temperature
            )
        except Exception as e:
            return SkillResult(success=False, error=f"LLM client creation failed: {e}")

        steps.append({"step": 1, "action": "ablation_analysis", "status": "running",
                       "result": f"正在对「{topic}」进行消融实验矩阵拟合分析..."})

        prompt = f"""你是一位资深的机器学习消融实验分析专家。请对以下主题进行消融实验矩阵拟合检测分析：

## 主题
{topic}

## 分析要求
1. **消融实验设计**：设计合理的消融实验方案，明确基线模型和各个组件
2. **矩阵拟合方法**：描述使用的矩阵拟合方法（如线性回归、样条拟合、核方法等）
3. **突变点检测**：识别消融曲线中的突变点，分析可能的异常特征噪音
4. **特征重要性排序**：基于消融结果对各特征/组件进行重要性排序
5. **可视化建议**：推荐合适的可视化方案（如消融曲线图、特征重要性柱状图等）
6. **结论与建议**：总结关键发现，提出改进建议

请用专业的中文学术风格输出，包含必要的公式（使用 LaTeX 格式）和数据表格。"""

        try:
            msg = [{"role": "user", "content": prompt}]
            resp = llm.invoke(msg)
            content = resp.content if hasattr(resp, "content") else str(resp)

            steps.append({"step": 2, "action": "report_generation", "status": "done",
                           "result": "消融实验分析报告生成完成"})

            # Auto-ingest into knowledge base
            try:
                from src.rag.retriever import ingest_text, is_rag_available
                if is_rag_available() and content and len(content) > 200:
                    ingest_text(text=content, title=f"消融实验分析 - {topic}", doc_type="ablation_analysis")
                    steps.append({"step": 3, "action": "knowledge_ingest", "status": "done",
                                   "result": "分析结果已自动入库"})
            except Exception:
                pass

            return SkillResult(
                success=True,
                content=content,
                steps=steps,
                duration_ms=int((time.time() - _start) * 1000),
            )
        except Exception as e:
            return SkillResult(
                success=False,
                error=f"Ablation analysis failed: {e}",
                steps=steps,
                duration_ms=int((time.time() - _start) * 1000),
            )
