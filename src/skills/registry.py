"""Skill Registry - manages registration, discovery, and loading of skills.

Skills can be:
1. Built-in: Included with the project
2. User-installed: Dropped into the skills_library/ directory
3. Dynamically loaded: From Python modules at runtime
"""
import sys
import importlib
import importlib.util
from pathlib import Path
from typing import Dict, List, Optional, Type

from src.skills.base import BaseSkill, SkillContext, SkillResult

# User skills directory
SKILLS_LIBRARY = Path(__file__).parent.parent.parent / "skills_library"


class SkillRegistry:
    """Central registry for all skills.
    
    Manages skill lifecycle:
    - Registration (built-in + user-installed)
    - Discovery (scan skills_library/ directory)
    - Loading (import Python modules)
    - Execution (invoke skills with context)
    """
    
    def __init__(self):
        self._skills: Dict[str, BaseSkill] = {}
        self._skill_classes: Dict[str, Type[BaseSkill]] = {}
        self._skill_sources: Dict[str, str] = {}  # name -> "builtin" | "user"
        self._load_builtin_skills()
        self._discover_user_skills()
    
    def _load_builtin_skills(self):
        """Load all built-in skills."""
        from src.skills.builtin.research_skill import ResearchSkill
        from src.skills.builtin.paper_skill import PaperWritingSkill
        from src.skills.builtin.survey_skill import SurveyWritingSkill
        from src.skills.builtin.code_review_skill import CodeReviewSkill
        from src.skills.builtin.literature_review_skill import LiteratureReviewSkill
        
        builtin = [
            ResearchSkill,
            PaperWritingSkill,
            SurveyWritingSkill,
            CodeReviewSkill,
            LiteratureReviewSkill,
        ]
        
        for skill_cls in builtin:
            self.register(skill_cls, source="builtin")
    
    def _discover_user_skills(self):
        """Discover and load user-installed skills from skills_library/."""
        if not SKILLS_LIBRARY.exists():
            return
        
        for skill_file in SKILLS_LIBRARY.glob("*_skill.py"):
            try:
                self._load_skill_file(skill_file, source="user")
            except Exception as e:
                print(f"Failed to load skill from {skill_file}: {e}")
    
    def _load_skill_file(self, filepath: Path, source: str = "user"):
        """Load a skill from a Python file."""
        module_name = f"user_skill_{filepath.stem}"
        spec = importlib.util.spec_from_file_location(module_name, filepath)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        
        # Find skill classes in the module
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and 
                issubclass(attr, BaseSkill) and 
                attr is not BaseSkill and
                hasattr(attr, 'name')):
                self.register(attr, source=source)
    
    # --- Registration ---
    
    def register(self, skill_cls: Type[BaseSkill], source: str = "builtin") -> BaseSkill:
        """Register a skill class.
        
        Args:
            skill_cls: Subclass of BaseSkill
            source: "builtin" or "user"
            
        Returns:
            Instantiated skill instance
        """
        instance = skill_cls()
        self._skills[instance.name] = instance
        self._skill_classes[instance.name] = skill_cls
        self._skill_sources[instance.name] = source
        return instance
    
    def unregister(self, skill_name: str) -> bool:
        """Unregister a skill."""
        if skill_name in self._skills:
            del self._skills[skill_name]
            del self._skill_classes[skill_name]
            return True
        return False
    
    # --- Discovery ---
    
    def list_skills(self, tag: Optional[str] = None) -> List[Dict]:
        """List all registered skills.
        
        Args:
            tag: Filter by tag (optional)
            
        Returns:
            List of skill info dicts
        """
        skills = self._skills.values()
        if tag:
            skills = [s for s in skills if tag in s.tags]
        return [s.get_info() for s in skills]
    
    def get_skill(self, name: str) -> Optional[BaseSkill]:
        """Get a skill by name."""
        return self._skills.get(name)
    
    def has_skill(self, name: str) -> bool:
        """Check if a skill is registered."""
        return name in self._skills
    
    def get_by_tag(self, tag: str) -> List[BaseSkill]:
        """Get all skills with a specific tag."""
        return [s for s in self._skills.values() if tag in s.tags]
    
    # --- Execution ---
    
    def execute(self, skill_name: str, context: SkillContext) -> SkillResult:
        """Execute a skill by name.
        
        Args:
            skill_name: Name of the skill to execute
            context: SkillContext with parameters
            
        Returns:
            SkillResult
        """
        skill = self._skills.get(skill_name)
        if not skill:
            return SkillResult(
                success=False,
                error=f"Skill '{skill_name}' not found. Available: {list(self._skills.keys())}"
            )
        return skill.run(context)
    
    def install_skill(self, filepath: Path) -> bool:
        """Install a skill from a Python file.
        
        Args:
            filepath: Path to the skill Python file
            
        Returns:
            True if successful
        """
        try:
            # Copy to skills_library
            SKILLS_LIBRARY.mkdir(parents=True, exist_ok=True)
            dest = SKILLS_LIBRARY / filepath.name
            dest.write_bytes(filepath.read_bytes())
            
            # Load it
            self._load_skill_file(dest, source="user")
            return True
        except Exception as e:
            print(f"Failed to install skill: {e}")
            return False
    
    def install_from_code(self, code: str, filename: str = "custom_skill.py") -> tuple[bool, str]:
        """Install a skill from Python source code string.
        
        Args:
            code: Python source code containing a BaseSkill subclass
            filename: File name to save as
            
        Returns:
            (success, message)
        """
        try:
            # Validate it's valid Python
            import ast
            ast.parse(code)
            
            # Save to skills_library
            SKILLS_LIBRARY.mkdir(parents=True, exist_ok=True)
            dest = SKILLS_LIBRARY / filename
            
            # Check name conflict
            if dest.exists():
                base = dest.stem
                counter = 1
                while dest.exists():
                    dest = SKILLS_LIBRARY / f"{base}_{counter}.py"
                    counter += 1
            
            dest.write_text(code, encoding="utf-8")
            
            # Load it
            self._load_skill_file(dest, source="user")
            
            # Find the skill name that was loaded
            for name in self._skill_sources:
                if self._skill_sources[name] == "user" and dest.name in str(dest):
                    return True, f"Skill '{name}' installed successfully"
            return True, f"Skill installed to {dest.name}"
        except SyntaxError as e:
            return False, f"Python syntax error: {e}"
        except Exception as e:
            return False, f"Install failed: {e}"
    
    def uninstall_skill(self, skill_name: str) -> tuple[bool, str]:
        """Uninstall a user-installed skill.
        
        Can only uninstall user skills, not built-in.
        Also deletes the source file.
        
        Returns:
            (success, message)
        """
        source = self._skill_sources.get(skill_name)
        if source != "user":
            return False, f"Cannot uninstall built-in skill '{skill_name}'"
        
        if skill_name not in self._skills:
            return False, f"Skill '{skill_name}' not found"
        
        # Remove from registry
        del self._skills[skill_name]
        if skill_name in self._skill_classes:
            del self._skill_classes[skill_name]
        del self._skill_sources[skill_name]
        
        # Delete the file
        file_to_delete = SKILLS_LIBRARY / f"{skill_name}.py"
        if file_to_delete.exists():
            file_to_delete.unlink()
        # Also check with _skill suffix
        file_to_delete = SKILLS_LIBRARY / f"{skill_name}_skill.py"
        if file_to_delete.exists():
            file_to_delete.unlink()
        
        return True, f"Skill '{skill_name}' uninstalled"
    
    def get_skill_source(self, skill_name: str) -> str:
        """Get source of a skill: 'builtin', 'user', or 'unknown'."""
        return self._skill_sources.get(skill_name, "unknown")
    
    def is_user_skill(self, skill_name: str) -> bool:
        """Check if a skill is user-installed (can be deleted)."""
        return self._skill_sources.get(skill_name) == "user"
    
    def reload_skills(self):
        """Reload all skills (built-in + user)."""
        self._skills.clear()
        self._skill_classes.clear()
        self._skill_sources.clear()
        self._load_builtin_skills()
        self._discover_user_skills()


# Singleton
_registry = None


def get_skill_registry() -> SkillRegistry:
    """Get SkillRegistry singleton."""
    global _registry
    if _registry is None:
        _registry = SkillRegistry()
    return _registry
