"""Literature Review Skill - Systematic literature review generation.

Produces structured literature reviews with:
- PRISMA-style methodology description
- Systematic search and screening
- Quality assessment
- Thematic synthesis
"""
from typing import Dict, List

from src.skills.base import BaseSkill, SkillResult, SkillContext
from src.models.manager import get_model_manager
from src.agent.tools import semantic_scholar_search, web_search


class LiteratureReviewSkill(BaseSkill):
    """Generate systematic literature reviews."""
    
    name = "literature_review"
    display_name = "Literature Review"
    description = "Generate systematic literature reviews with PRISMA methodology, quality assessment tables, and thematic synthesis. Ideal for thesis chapters and survey papers."
    version = "1.0.0"
    author = "CS599 Agent"
    tags = ["research", "literature", "review", "academic"]
    
    parameters_schema = {
        "topic": {
            "type": "string",
            "description": "Review topic with research question",
            "required": True,
        },
        "methodology": {
            "type": "string",
            "description": "Review methodology",
            "options": ["prisma", "systematic", "narrative", "scoping"],
            "default": "prisma",
        },
        "time_range": {
            "type": "string",
            "description": "Publication time range",
            "options": ["last_year", "last_3_years", "last_5_years", "all"],
            "default": "last_5_years",
        },
    }
    
    def execute(self, context: SkillContext) -> SkillResult:
        """Generate systematic literature review."""
        topic = context.topic
        params = context.custom_params
        methodology = params.get("methodology", "prisma")
        time_range = params.get("time_range", "last_5_years")
        
        manager = get_model_manager()
        llm = manager.create_llm_client(
            context.provider_name, context.model_id, context.temperature
        )
        
        steps = []
        
        # Step 1: Search for papers
        steps.append({"step": 1, "action": "search", "status": "running"})
        papers = self._search_papers(topic)
        steps[-1]["status"] = "done"
        steps[-1]["result"] = f"Found {len(papers)} papers"
        
        # Step 2: Screening and selection
        steps.append({"step": 2, "action": "screening", "status": "running"})
        selected = self._screen_papers(llm, topic, papers)
        steps[-1]["status"] = "done"
        steps[-1]["result"] = f"Selected {len(selected)} papers"
        
        # Step 3: Quality assessment
        steps.append({"step": 3, "action": "quality_assessment", "status": "running"})
        quality = self._assess_quality(llm, selected)
        steps[-1]["status"] = "done"
        
        # Step 4: Thematic synthesis
        steps.append({"step": 4, "action": "synthesis", "status": "running"})
        synthesis = self._synthesize_themes(llm, topic, selected)
        steps[-1]["status"] = "done"
        
        # Step 5: Generate review
        steps.append({"step": 5, "action": "generate", "status": "running"})
        review = self._generate_review(llm, topic, methodology, time_range, 
                                       papers, selected, quality, synthesis)
        steps[-1]["status"] = "done"
        
        return SkillResult(
            success=True,
            content=review,
            metadata={
                "methodology": methodology,
                "time_range": time_range,
                "total_papers": len(papers),
                "selected_papers": len(selected),
            },
            steps=steps,
            sources=[{"title": p["title"], "url": p["url"], "type": p["type"]} for p in selected],
        )
    
    def _search_papers(self, topic: str) -> List[Dict]:
        """Search for academic papers."""
        papers = []
        for r in semantic_scholar_search(topic, max_results=10):
            papers.append({"title": r.title, "url": r.url, "type": "semantic_scholar", 
                          "abstract": r.snippet, "year": "", "venue": "arXiv"})
        return papers
    
    def _screen_papers(self, llm, topic: str, papers: List[Dict]) -> List[Dict]:
        """Screen and select relevant papers."""
        paper_list = "\n".join(f"{i+1}. {p['title']}" for i, p in enumerate(papers))
        prompt = f"""Select the most relevant papers for: {topic}

Papers:
{paper_list}

Return only the numbers of papers to include (5-8 papers), as a JSON array."""
        
        try:
            import json, re
            response = llm.invoke([{"role": "user", "content": prompt}])
            content = response.content if hasattr(response, 'content') else str(response)
            match = re.search(r'\[.*?\]', content)
            if match:
                indices = json.loads(match.group())
                return [papers[i-1] for i in indices if 1 <= i <= len(papers)]
        except Exception:
            pass
        return papers[:8]
    
    def _assess_quality(self, llm, papers: List[Dict]) -> str:
        """Assess quality of selected papers."""
        prompt = f"""Create a quality assessment table for these papers:

"""
        for p in papers:
            prompt += f"- {p['title']}\n"
        
        prompt += """

Create a Markdown table with columns: Paper, Relevance, Methodology, Novelty, Overall Score (1-5).

Also include a brief quality summary paragraph."""
        
        try:
            response = llm.invoke([{"role": "user", "content": prompt}])
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            return f"<!-- Quality assessment error: {e} -->"
    
    def _synthesize_themes(self, llm, topic: str, papers: List[Dict]) -> str:
        """Identify and synthesize themes."""
        abstracts = "\n\n".join(f"Paper: {p['title']}\nAbstract: {p['abstract'][:500]}" 
                               for p in papers)
        
        prompt = f"""Identify 3-5 key themes in the literature on: {topic}

Based on these paper abstracts:
{abstracts}

For each theme:
1. Theme name
2. Description (2-3 sentences)
3. Key papers supporting this theme
4. Any disagreements or debates

Output in Markdown format."""
        
        try:
            response = llm.invoke([{"role": "user", "content": prompt}])
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            return f"<!-- Synthesis error: {e} -->"
    
    def _generate_review(self, llm, topic: str, methodology: str, time_range: str,
                         all_papers: List[Dict], selected: List[Dict], 
                         quality: str, synthesis: str) -> str:
        """Generate the final literature review."""
        prompt = f"""Write a systematic literature review on: {topic}

Methodology: {methodology.upper()}
Time Range: {time_range}
Total papers found: {len(all_papers)}
Papers included: {len(selected)}

Quality Assessment:
{quality}

Thematic Synthesis:
{synthesis}

Generate a complete literature review with:

# Systematic Literature Review: {topic}

## Abstract
200 words, structured (Background, Methods, Results, Conclusion)

## 1. Introduction
- Research question
- Motivation
- Scope

## 2. Methodology
- Search strategy (databases, keywords)
- Selection criteria (inclusion/exclusion)
- Quality assessment method

## 3. Results
- Search results summary
- Quality assessment results
- Thematic analysis

## 4. Discussion
- Key findings
- Comparison with existing reviews
- Implications

## 5. Conclusion
- Summary
- Limitations
- Future research directions

## References
List included papers"""
        
        try:
            response = llm.invoke([{"role": "user", "content": prompt}])
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            return f"# Literature Review: {topic}\n\n## Error\n{e}"
