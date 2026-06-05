"""Survey Writing Skill - Generate comprehensive survey/review documents.

Produces structured survey papers with taxonomy, comparative analysis,
and comprehensive coverage of a research area.
"""
from typing import Dict, List

from src.skills.base import BaseSkill, SkillResult, SkillContext
from src.models.manager import get_model_manager
from src.agent.tools import web_search, semantic_scholar_search


class SurveyWritingSkill(BaseSkill):
    """Generate comprehensive survey/review papers."""
    
    name = "survey_writing"
    display_name = "Survey / Review Writer"
    description = "Generate comprehensive survey or review documents with taxonomy, comparative tables, and systematic coverage of a research area. Ideal for literature reviews and state-of-the-art summaries."
    version = "2.0.0"
    author = "CS599 Agent"
    tags = ["writing", "survey", "review", "taxonomy"]
    
    parameters_schema = {
        "topic": {
            "type": "string",
            "description": "Survey topic",
            "required": True,
        },
        "scope": {
            "type": "string",
            "description": "Scope of survey",
            "options": ["broad", "focused", "comparative"],
            "default": "focused",
        },
        "taxonomy": {
            "type": "boolean",
            "description": "Include taxonomy/ classification",
            "default": True,
        },
        "comparisons": {
            "type": "boolean",
            "description": "Include comparison tables",
            "default": True,
        },
    }
    
    def execute(self, context: SkillContext) -> SkillResult:
        """Generate survey document."""
        topic = context.topic
        params = context.custom_params
        scope = params.get("scope", "focused")
        include_taxonomy = params.get("taxonomy", True)
        include_comparisons = params.get("comparisons", True)
        
        manager = get_model_manager()
        llm = manager.create_llm_client(
            context.provider_name, context.model_id, context.temperature
        )
        
        steps = []
        
        # Step 1: Gather sources
        steps.append({"step": 1, "action": "gather_sources", "status": "running"})
        sources = self._gather_sources(topic)
        steps[-1]["status"] = "done"
        steps[-1]["result"] = f"Found {len(sources)} sources"
        
        # Step 2: Build taxonomy
        taxonomy = None
        if include_taxonomy:
            steps.append({"step": 2, "action": "build_taxonomy", "status": "running"})
            taxonomy = self._build_taxonomy(llm, topic, sources)
            steps[-1]["status"] = "done"
        
        # Step 3: Comparative analysis
        comparisons = None
        if include_comparisons:
            steps.append({"step": 3, "action": "comparative_analysis", "status": "running"})
            comparisons = self._comparative_analysis(llm, topic, sources)
            steps[-1]["status"] = "done"
        
        # Step 4: Write survey
        steps.append({"step": 4, "action": "write_survey", "status": "running"})
        survey = self._write_survey(llm, topic, sources, taxonomy, comparisons, scope)
        steps[-1]["status"] = "done"
        
        return SkillResult(
            success=True,
            content=survey,
            metadata={
                "scope": scope,
                "num_sources": len(sources),
                "has_taxonomy": include_taxonomy,
                "has_comparisons": include_comparisons,
            },
            steps=steps,
            sources=sources,
        )
    
    def _gather_sources(self, topic: str) -> List[Dict]:
        """Gather sources for the survey."""
        sources = []
        for r in semantic_scholar_search(topic, max_results=8):
            sources.append({"title": r.title, "url": r.url, "type": "semantic_scholar", "snippet": r.snippet})
        for r in web_search(f"{topic} survey review", max_results=5):
            sources.append({"title": r.title, "url": r.url, "type": "web", "snippet": r.snippet})
        return sources
    
    def _build_taxonomy(self, llm, topic: str, sources: List[Dict]) -> str:
        """Build a taxonomy/classification of the field."""
        snippets = "\n".join(s.get("snippet", "")[:500] for s in sources[:5])
        prompt = f"""Create a taxonomy/classification tree for the field: {topic}

Based on these sources:
{snippets}

Generate a hierarchical taxonomy in Markdown format using nested lists.
Format:
- Category 1
  - Subcategory 1.1
  - Subcategory 1.2
- Category 2
  - Subcategory 2.1
    - Method A
    - Method B

Output only the taxonomy."""
        
        try:
            response = llm.invoke([{"role": "user", "content": prompt}])
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            return f"<!-- Error building taxonomy: {e} -->"
    
    def _comparative_analysis(self, llm, topic: str, sources: List[Dict]) -> str:
        """Create comparison tables of approaches."""
        prompt = f"""Create comparison tables for different approaches in: {topic}

Create 2-3 tables comparing:
1. Methods/approaches (columns: Method, Key Idea, Strengths, Limitations)
2. Datasets or benchmarks (if applicable)
3. Performance metrics (if applicable)

Use Markdown table format. Output only the tables."""
        
        try:
            response = llm.invoke([{"role": "user", "content": prompt}])
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            return f"<!-- Error: {e} -->"
    
    def _write_survey(self, llm, topic: str, sources: List[Dict], 
                      taxonomy: str, comparisons: str, scope: str) -> str:
        """Write the complete survey document."""
        sources_text_lines = []
        for s in sources[:15]:
            sources_text_lines.append(f"- [{s['title']}]({s['url']}) ({s['type']})")
        sources_text = "\n".join(sources_text_lines)
        
        taxonomy_section = "Taxonomy:\n" + taxonomy if taxonomy else ""
        comparisons_section = "Comparisons:\n" + comparisons if comparisons else ""
        
        prompt = f"""Write a comprehensive survey document on: {topic}

Scope: {scope}

Sources to reference:
{sources_text}

{taxonomy_section}

{comparisons_section}

Generate a survey document with:

# Survey: {topic}

## Abstract
Brief overview (200 words)

## 1. Introduction
Background, motivation, scope of survey

## 2. Taxonomy and Classification
Use the provided taxonomy

## 3. Methods and Approaches
Detailed review of key methods

## 4. Comparative Analysis
Use comparison tables

## 5. Datasets and Benchmarks
Standard evaluation resources

## 6. Challenges and Future Directions
Open problems and emerging trends

## 7. Conclusion

## References
Key papers cited"""
        
        try:
            response = llm.invoke([{"role": "user", "content": prompt}])
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            return f"# Survey: {topic}\n\n## Error\n{e}"
