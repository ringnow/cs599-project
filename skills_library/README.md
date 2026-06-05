# Skills Library

Place your custom skill Python files here.
Files ending with `_skill.py` will be auto-discovered.

## Example

```python
# my_skill.py
from src.skills.base import BaseSkill, SkillResult, SkillContext

class MySkill(BaseSkill):
    name = "my_skill"
    display_name = "My Custom Skill"
    description = "A custom skill for my research"
    tags = ["custom", "research"]

    def execute(self, context: SkillContext) -> SkillResult:
        # Your implementation
        return SkillResult(success=True, content="Result")
```
