"""Skills system - plugin-based research and writing capabilities.

Skills are modular, swappable components that provide specific capabilities
to the agent system. Each skill is self-contained and can be registered
with the skill registry at runtime.
"""
from src.skills.base import BaseSkill, SkillResult, SkillContext
from src.skills.registry import SkillRegistry, get_skill_registry
from src.skills.builtin.research_skill import ResearchSkill
from src.skills.builtin.paper_skill import PaperWritingSkill
from src.skills.builtin.survey_skill import SurveyWritingSkill

__all__ = [
    "BaseSkill",
    "SkillResult",
    "SkillContext",
    "SkillRegistry",
    "get_skill_registry",
    "ResearchSkill",
    "PaperWritingSkill",
    "SurveyWritingSkill",
]
