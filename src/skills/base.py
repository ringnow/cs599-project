"""Base classes for the skills system."""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import json


@dataclass
class SkillResult:
    """Result of executing a skill."""
    success: bool
    content: str = ""                      # Main output content
    metadata: Dict[str, Any] = field(default_factory=dict)  # Extra data
    steps: List[Dict] = field(default_factory=list)  # Execution steps
    error: str = ""                        # Error message if failed
    duration_ms: int = 0                   # Execution time
    sources: List[Dict] = field(default_factory=list)  # Source references


@dataclass
class SkillContext:
    """Context passed to skills during execution."""
    topic: str = ""                        # Research topic
    provider_name: str = "deepseek"        # LLM provider to use
    model_id: str = "deepseek-chat"        # Model to use
    temperature: float = 0.7
    max_iterations: int = 3
    sub_questions: List[str] = field(default_factory=list)
    previous_results: List['SkillResult'] = field(default_factory=list)
    custom_params: Dict[str, Any] = field(default_factory=dict)
    session_id: str = ""                   # Session tracking
    user_id: str = ""                      # JWT-authenticated user, if any
    
    def to_dict(self) -> dict:
        return {
            "topic": self.topic,
            "provider_name": self.provider_name,
            "model_id": self.model_id,
            "temperature": self.temperature,
            "max_iterations": self.max_iterations,
            "sub_questions": self.sub_questions,
            "custom_params": self.custom_params,
            "session_id": self.session_id,
        }


class BaseSkill(ABC):
    """Base class for all skills.
    
    Skills are modular capabilities that can be registered and invoked
    by the agent system. Each skill has a name, description, and
    parameter schema.
    """
    
    # Skill metadata - override in subclasses
    name: str = "base_skill"
    display_name: str = "Base Skill"
    description: str = "Base skill description"
    version: str = "1.0.0"
    author: str = ""
    tags: List[str] = []
    
    # Parameter schema for UI generation
    parameters_schema: Dict[str, Any] = {}
    
    def __init__(self):
        self.created_at = datetime.now().isoformat()
        self.invocation_count = 0
    
    @abstractmethod
    def execute(self, context: SkillContext) -> SkillResult:
        """Execute the skill with given context.
        
        Args:
            context: SkillContext with parameters and state
            
        Returns:
            SkillResult with output content and metadata
        """
        pass
    
    def validate_params(self, context: SkillContext) -> tuple[bool, str]:
        """Validate parameters before execution.
        
        Returns:
            (is_valid, error_message)
        """
        if not context.topic:
            return False, "Topic is required"
        return True, ""
    
    def pre_execute(self, context: SkillContext) -> SkillContext:
        """Hook called before execution. Can modify context."""
        return context
    
    def post_execute(self, result: SkillResult, context: SkillContext) -> SkillResult:
        """Hook called after execution. Can modify result."""
        return result
    
    def run(self, context: SkillContext) -> SkillResult:
        """Full execution pipeline with validation and hooks."""
        import time
        from src.api.cancel import is_cancelled, clear as clear_cancelled

        # Validate
        valid, error = self.validate_params(context)
        if not valid:
            return SkillResult(success=False, error=error)

        # Pre-execute
        context = self.pre_execute(context)

        # 取消检查：在执行前检查是否已被取消
        request_id = context.custom_params.get("request_id", "")
        if request_id and is_cancelled(request_id):
            return SkillResult(
                success=False,
                error="任务已被用户取消",
                content="任务已被用户取消。",
            )

        # Execute
        start = time.time()
        try:
            result = self.execute(context)
        except Exception as e:
            result = SkillResult(success=False, error=str(e))

        result.duration_ms = int((time.time() - start) * 1000)

        # Post-execute
        result = self.post_execute(result, context)

        # 清理取消标记，避免 _cancelled 字典无限增长
        if request_id:
            clear_cancelled(request_id)

        # 自动保存搜索历史到数据库（所有技能执行后统一写入）
        try:
            self._save_search_history(context, result)
        except Exception:
            pass  # 静默失败，不影响主流程

        # 自动入库到 RAG 知识库（所有技能执行后统一写入）
        try:
            self._ingest_to_rag(context, result)
        except Exception:
            pass

        # 自动写入 memory 知识图谱（所有技能执行后统一写入）
        try:
            self._save_to_memory(context, result)
        except Exception:
            pass

        self.invocation_count += 1
        return result

    def _save_search_history(self, context: SkillContext, result: SkillResult) -> None:
        """Save search history record after skill execution."""
        import time as _time
        from src.storage.database import SessionLocal, save_search
        db = SessionLocal()
        try:
            num_sources = result.metadata.get("num_sources", 0) or len(result.sources)
            num_papers = result.metadata.get("num_papers_cited", 0) or \
                         sum(1 for s in result.sources if s.get("type") == "paper")
            save_search(
                db_session=db,
                topic=context.topic,
                sub_questions=context.sub_questions,
                num_sources=num_sources,
                num_papers_cited=num_papers,
                report_preview=result.content[:500] if result.content else "",
                duration_seconds=result.duration_ms / 1000.0,
                provider=context.provider_name,
                model=context.model_id,
                username=context.user_id or None,
            )
        finally:
            db.close()

    def _save_to_memory(self, context: SkillContext, result: SkillResult) -> None:
        """研究结束后自动写入 memory 知识图谱。"""
        try:
            from src.mcp.manager import get_mcp_manager
            mgr = get_mcp_manager()
            if not mgr.is_server_enabled("memory_stdio"):
                return
            topic = context.topic
            preview = result.content[:200] if result.content else ""
            if preview:
                mgr.call_tool("memory_stdio", "create_entities", {
                    "entities": [{
                        "name": topic,
                        "entityType": "research_topic",
                        "observations": [preview],
                    }]
                })
        except Exception:
            pass

    def _ingest_to_rag(self, context: SkillContext, result: SkillResult) -> None:
        """自动将生成内容入库到 RAG 知识库。"""
        try:
            from src.rag.retriever import ingest_text, is_rag_available
            if not is_rag_available():
                return
            content = result.content
            if not content or len(content) < 200:
                return
            topic = context.topic or "unnamed"
            ingest_text(text=content, title=topic, doc_type="generated_report",
                        username=context.user_id or None)
        except Exception:
            pass
    
    def get_info(self) -> Dict[str, Any]:
        """Get skill information for display."""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "tags": self.tags,
            "parameters_schema": self.parameters_schema,
            "invocation_count": self.invocation_count,
            "created_at": self.created_at,
        }
    
    def __repr__(self):
        return f"<Skill {self.name} v{self.version}>"
