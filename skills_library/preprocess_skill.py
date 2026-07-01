"""实验数据预处理 Skill — 自动化数据清洗、归一化与特征工程。"""
import json
import time
from typing import Dict, Any, List

from src.skills.base import BaseSkill, SkillResult, SkillContext
from src.models.manager import get_model_manager


class DataPreprocessSkill(BaseSkill):
    """Automated data preprocessing — cleaning, normalization, and feature engineering."""

    name = "data_preprocess"
    display_name = "实验数据预处理"
    description = "自动化数据清洗、归一化与特征工程。对实验数据进行预处理，包括缺失值处理、异常值检测、数据标准化、特征编码等操作。"
    version = "1.0.0"
    author = "CS599 Agent"
    tags = ["分析", "数据预处理", "特征工程"]

    parameters_schema = {
        "topic": {"type": "string", "description": "数据预处理任务描述", "required": True},
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

        steps.append({"step": 1, "action": "preprocess_planning", "status": "running",
                       "result": f"正在为「{topic}」设计数据预处理方案..."})

        prompt = f"""你是一位专业的数据科学家，请为以下实验数据预处理任务提供完整的处理方案：

## 任务描述
{topic}

## 分析要求
1. **数据概况分析**：描述预期的数据结构、特征类型（数值型/类别型/文本型等）
2. **缺失值处理策略**：建议合适的缺失值处理方法（删除/均值填充/中位数填充/插值等）
3. **异常值检测与处理**：推荐异常值检测方法（IQR/Z-Score/DBSCAN/Isolation Forest等）
4. **数据标准化/归一化**：选择合适的标准化方法（Min-Max/Z-Score/RobustScaler等）
5. **特征编码**：对类别特征推荐编码方式（One-Hot/Label/Target Encoding等）
6. **特征工程建议**：推荐特征交叉、多项式特征、降维等策略
7. **数据划分策略**：建议训练/验证/测试集的划分方法

请用专业的中文学术风格输出，包含可执行的 Python 代码示例（使用 pandas/sklearn）。"""

        try:
            msg = [{"role": "user", "content": prompt}]
            resp = llm.invoke(msg)
            content = resp.content if hasattr(resp, "content") else str(resp)

            steps.append({"step": 2, "action": "report_generation", "status": "done",
                           "result": "数据预处理方案生成完成"})

            # Auto-ingest into knowledge base
            try:
                from src.rag.retriever import ingest_text, is_rag_available
                if is_rag_available() and content and len(content) > 200:
                    ingest_text(text=content, title=f"实验数据预处理 - {topic}", doc_type="preprocess_plan")
                    steps.append({"step": 3, "action": "knowledge_ingest", "status": "done",
                                   "result": "预处理方案已自动入库"})
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
                error=f"Data preprocessing failed: {e}",
                steps=steps,
                duration_ms=int((time.time() - _start) * 1000),
            )
