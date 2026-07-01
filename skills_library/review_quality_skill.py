"""文献综述质量评估 Skill — 自动评估综述论文的完整性、逻辑性和学术规范性。"""
import json
import time
from typing import Dict, Any, List

from src.skills.base import BaseSkill, SkillResult, SkillContext
from src.models.manager import get_model_manager


class ReviewQualitySkill(BaseSkill):
    """Literature review quality assessment — evaluate completeness, logic, and academic standards."""

    name = "review_quality"
    display_name = "文献综述质量评估"
    description = "自动评估综述论文的完整性、逻辑性和学术规范性。从覆盖度、逻辑结构、引用质量、创新性等维度对综述进行全面评价。"
    version = "1.0.0"
    author = "CS599 Agent"
    tags = ["分析", "文献综述", "质量评估"]

    parameters_schema = {
        "topic": {"type": "string", "description": "文献综述评估主题或待评估的综述内容", "required": True},
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

        steps.append({"step": 1, "action": "quality_assessment", "status": "running",
                       "result": f"正在对「{topic}」进行文献综述质量评估..."})

        prompt = f"""你是一位资深的学术评审专家，请对以下文献综述进行全面的质量评估：

## 综述主题/内容
{topic}

## 评估维度与标准
1. **覆盖度 (Coverage)** (0-10分)：
   - 是否涵盖该领域的关键文献和里程碑工作
   - 是否包含近3-5年的前沿进展
   - 对经典文献和最新文献的平衡

2. **逻辑结构 (Logical Structure)** (0-10分)：
   - 整体组织结构是否清晰合理
   - 章节之间逻辑过渡是否自然
   - 论证链条是否完整

3. **引用质量 (Citation Quality)** (0-10分)：
   - 引用来源的权威性和代表性
   - 引用的准确性和相关性
   - 是否适当引用综述性文献

4. **批判性分析 (Critical Analysis)** (0-10分)：
   - 是否不仅仅是文献罗列
   - 是否对现有工作进行客观评价
   - 是否指出研究空白和局限性

5. **创新性与洞见 (Innovation & Insight)** (0-10分)：
   - 是否提出新的分类框架或视角
   - 是否识别未来研究方向
   - 是否具有方法论贡献

6. **学术规范性 (Academic Standards)** (0-10分)：
   - 语言表达的学术性
   - 引用格式规范性
   - 图表和表格的专业性

## 输出格式
请按以上 6 个维度逐项评分并给出详细评语，最后给出综合评分和修改建议。"""

        try:
            msg = [{"role": "user", "content": prompt}]
            resp = llm.invoke(msg)
            content = resp.content if hasattr(resp, "content") else str(resp)

            steps.append({"step": 2, "action": "report_generation", "status": "done",
                           "result": "质量评估报告生成完成"})

            # Auto-ingest into knowledge base
            try:
                from src.rag.retriever import ingest_text, is_rag_available
                if is_rag_available() and content and len(content) > 200:
                    ingest_text(text=content, title=f"文献综述质量评估 - {topic}", doc_type="quality_assessment")
                    steps.append({"step": 3, "action": "knowledge_ingest", "status": "done",
                                   "result": "评估结果已自动入库"})
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
                error=f"Quality assessment failed: {e}",
                steps=steps,
                duration_ms=int((time.time() - _start) * 1000),
            )
