"""Survey Writing Skill - Generate comprehensive survey/review documents.

Produces structured survey papers with taxonomy, comparative analysis,
and comprehensive coverage of a research area.
"""
from typing import Dict, List

from src.skills.base import BaseSkill, SkillResult, SkillContext
from src.models.manager import get_model_manager
from src.agent.tools import web_search, semantic_scholar_search, extract_paper_content
from src.agent.state import SearchResult


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
        evaluated_papers = []
        worth_citing_papers = []

        # Step 1: Gather sources (injects MCP arxiv papers into ss_results)
        steps.append({"step": 1, "action": "gather_sources", "status": "running"})
        sources, ss_results = self._gather_sources(topic, context)
        arxiv_count = sum(1 for r in ss_results if r.source == "arxiv")
        steps[-1]["status"] = "done"
        steps[-1]["result"] = f"Found {len(sources)} sources" + (f" ({arxiv_count} from MCP arxiv)" if arxiv_count else "")

        # Step 1b: Evaluate academic papers using ResearchSkill's pipeline
        if ss_results:
            steps.append({"step": 2, "action": "evaluate_papers", "status": "running"})
            try:
                from src.skills.builtin.research_skill import ResearchSkill
                rs = ResearchSkill()
                for r in ss_results:
                    content = extract_paper_content(r)
                    r.content = content or (r.snippet[:2000] if r.snippet else "")
                academic_papers = [r for r in ss_results if r.content]
                if academic_papers:
                    evaluated_papers = rs._evaluate_papers(llm, academic_papers, topic, context.custom_params.get("request_id", ""))
                    worth_citing_papers = [ev for ev in evaluated_papers if ev.get("worth_citing")]
                    steps[-1]["status"] = "done"
                    steps[-1]["result"] = f"Evaluated {len(evaluated_papers)} papers, {len(worth_citing_papers)} worth citing"
                else:
                    steps[-1]["status"] = "warning"
                    steps[-1]["result"] = "No academic papers with content to evaluate"
            except Exception as eval_e:
                steps[-1]["status"] = "warning"
                steps[-1]["result"] = f"Paper evaluation skipped: {eval_e}"
        # Step 3: Build taxonomy (was step 2)
        next_step = 3
        taxonomy = None
        if include_taxonomy:
            steps.append({"step": next_step, "action": "build_taxonomy", "status": "running"})
            taxonomy = self._build_taxonomy(llm, topic, sources)
            steps[-1]["status"] = "done"
            next_step += 1

        # Step 4: Comparative analysis (was step 3)
        comparisons = None
        if include_comparisons:
            steps.append({"step": next_step, "action": "comparative_analysis", "status": "running"})
            comparisons = self._comparative_analysis(llm, topic, sources)
            steps[-1]["status"] = "done"
            next_step += 1

        # Step 5: Write survey (was step 4)
        steps.append({"step": next_step, "action": "write_survey", "status": "running"})
        survey = self._write_survey(llm, topic, sources, taxonomy, comparisons, scope, evaluated_papers, worth_citing_papers)
        steps[-1]["status"] = "done"
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
    
    def _gather_sources(self, topic: str, context: SkillContext = None) -> tuple:
        """Gather sources for the survey.

        If context is provided, MCP arxiv papers from context.custom_params['mcp_search_results']
        are converted to SearchResult objects and merged into ss_results so they enter the
        same LLM evaluation pipeline as Semantic Scholar papers.

        Returns:
            (sources_dicts, ss_orig) — dicts for prompt building,
            original SearchResult objects for LLM evaluation.
        """
        ss_results = semantic_scholar_search(topic, max_results=8)
        web_results = web_search(f"{topic} survey review", max_results=5)

        # Inject MCP arxiv papers into ss_results so they go through _evaluate_papers
        if context is not None:
            mcp_results = context.custom_params.get("mcp_search_results", [])
            for mr in mcp_results:
                try:
                    snippet = mr.get("snippet", "")
                    ss_results.append(SearchResult(
                        title=mr.get("title", ""),
                        url=mr.get("url", ""),
                        snippet=snippet,
                        content=snippet,
                        source="arxiv",
                        year=mr.get("year", 0),
                        authors=mr.get("authors", []),
                    ))
                except Exception:
                    pass

        sources = []
        for r in ss_results:
            src_type = "arxiv" if r.source == "arxiv" else "semantic_scholar"
            sources.append({"title": r.title, "url": r.url, "type": src_type, "snippet": r.snippet})
        for r in web_results:
            sources.append({"title": r.title, "url": r.url, "type": "web", "snippet": r.snippet})
        return sources, ss_results
    
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
                      taxonomy: str, comparisons: str, scope: str,
                      evaluated_papers: List[Dict] = None,
                      worth_citing_papers: List[Dict] = None) -> str:
        """Write the complete survey document."""
        # Build sources text from evaluated papers if available
        if evaluated_papers:
            sources_text_lines = []
            for idx, ev in enumerate(evaluated_papers, 1):
                icon = "📄" if ev.get("worth_citing") else "📋"
                sources_text_lines.append(f"{icon} [{idx}] {ev['title']} — {ev.get('relevance', '?')}")
            sources_text = "\n".join(sources_text_lines[:15])

            # Add full verified references section
            if worth_citing_papers:
                ref_lines = []
                for idx, ev in enumerate(worth_citing_papers, 1):
                    authors = ev.get("authors", [])
                    authors_str = ", ".join(authors[:3]) if authors else ""
                    ref = f"[{idx}] {ev['title']}"
                    if authors_str:
                        ref += f". {authors_str}"
                    if ev.get("year"):
                        ref += f" ({ev['year']})"
                    if ev.get("journal"):
                        ref += f". {ev['journal']}"
                    ref_lines.append(ref)
                refs_text = "\n\nVerified References:\n" + "\n".join(ref_lines)
            else:
                refs_text = ""
        else:
            sources_text_lines = []
            for s in sources[:15]:
                sources_text_lines.append(f"- [{s['title']}]({s['url']}) ({s['type']})")
            sources_text = "\n".join(sources_text_lines)
            refs_text = ""

        taxonomy_section = "Taxonomy:\n" + taxonomy if taxonomy else ""
        comparisons_section = "Comparisons:\n" + comparisons if comparisons else ""

        prompt = f"""Write a comprehensive survey document on: {topic}

Scope: {scope}

Sources to reference (cite using [N] format):
{sources_text}

{taxonomy_section}

{comparisons_section}
{refs_text}

Requirements:
- ONLY cite sources from the list above
- Do NOT fabricate references
- Use [N] citation format matching the numbered sources above

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
Cite the sources listed above using [N] format"""

        try:
            response = llm.invoke([{"role": "user", "content": prompt}])
            content = response.content if hasattr(response, 'content') else str(response)
            # Append real verified references
            if worth_citing_papers:
                real_refs = "\n\n## Verified References (Real Academic Papers)\n\n"
                for idx, ev in enumerate(worth_citing_papers, 1):
                    authors = ev.get("authors", [])
                    authors_str = ", ".join(authors[:3]) if authors else ""
                    ref = f"[{idx}] {ev['title']}"
                    if authors_str:
                        ref += f". {authors_str}"
                    if ev.get("year"):
                        ref += f" ({ev['year']})"
                    if ev.get("journal"):
                        ref += f". {ev['journal']}"
                    if ev.get("url"):
                        ref += f". {ev['url']}"
                    if ev.get("key_findings"):
                        ref += f" — {ev['key_findings'][:100]}"
                    real_refs += ref + "\n\n"
                real_refs += "\n*These references are real academic papers that were read and evaluated by LLM.*\n"
                content += real_refs
            return content
        except Exception as e:
            return f"# Survey: {topic}\n\n## Error\n{e}"
