"""Code Review Skill - Automated code review and analysis.

Reviews code for:
- Bugs and potential errors
- Security vulnerabilities
- Performance issues
- Code style and best practices
- Documentation quality
"""
from typing import Dict, List

from src.skills.base import BaseSkill, SkillResult, SkillContext
from src.models.manager import get_model_manager


class CodeReviewSkill(BaseSkill):
    """Automated code review and quality analysis."""
    
    name = "code_review"
    display_name = "Code Reviewer"
    description = "Review code for bugs, security issues, performance problems, and style violations. Supports Python, JavaScript, TypeScript, Java, C++, and other languages."
    version = "1.0.0"
    author = "CS599 Agent"
    tags = ["code", "review", "quality", "security"]
    
    parameters_schema = {
        "code": {
            "type": "string",
            "description": "Code to review",
            "required": True,
        },
        "language": {
            "type": "string",
            "description": "Programming language",
            "default": "python",
        },
        "focus": {
            "type": "array",
            "description": "Review focus areas",
            "options": ["bugs", "security", "performance", "style", "documentation"],
            "default": ["bugs", "security", "performance"],
        },
    }
    
    def validate_params(self, context: SkillContext) -> tuple[bool, str]:
        code = context.custom_params.get("code", "")
        if not code:
            return False, "Code is required for review"
        return True, ""
    
    def execute(self, context: SkillContext) -> SkillResult:
        """Execute code review."""
        params = context.custom_params
        code = params.get("code", "")
        language = params.get("language", "python")
        focus = params.get("focus", ["bugs", "security", "performance"])
        
        manager = get_model_manager()
        llm = manager.create_llm_client(
            context.provider_name, context.model_id, context.temperature
        )
        
        focus_text = ", ".join(focus)
        
        prompt = f"""Perform a thorough code review of the following {language} code.

Focus areas: {focus_text}

```{language}
{code}
```

Please provide:

## 1. Summary
Brief overview of code quality (2-3 sentences)

## 2. Issues Found
For each issue:
- **Severity**: Critical / High / Medium / Low
- **Category**: Bug / Security / Performance / Style
- **Location**: Line numbers
- **Description**: What's wrong
- **Suggestion**: How to fix it

## 3. Positive Aspects
What the code does well

## 4. Recommendations
Top 3 actionable improvements

## 5. Refactored Code
Provide improved version if applicable

Format as Markdown. Be specific and actionable."""
        
        try:
            response = llm.invoke([{"role": "user", "content": prompt}])
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Count issues
            issue_count = content.count("**Severity**:")
            
            return SkillResult(
                success=True,
                content=content,
                metadata={
                    "language": language,
                    "focus_areas": focus,
                    "issue_count": issue_count,
                    "code_length": len(code),
                },
            )
        except Exception as e:
            return SkillResult(success=False, error=str(e))
