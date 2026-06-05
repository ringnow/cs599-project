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
        
        # Validate
        valid, error = self.validate_params(context)
        if not valid:
            return SkillResult(success=False, error=error)
        
        # Pre-execute
        context = self.pre_execute(context)
        
        # Execute
        start = time.time()
        try:
            result = self.execute(context)
        except Exception as e:
            result = SkillResult(success=False, error=str(e))
        
        result.duration_ms = int((time.time() - start) * 1000)
        
        # Post-execute
        result = self.post_execute(result, context)
        
        self.invocation_count += 1
        return result
    
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
