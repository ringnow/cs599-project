"""Paper Writing Skill - Generate academic papers with proper structure.

Generates complete academic papers including:
- Abstract
- Introduction
- Related Work
- Methodology
- Experiments/Results
- Conclusion
- References

Can produce papers in multiple styles: research paper, survey paper, short paper.
"""
from typing import Dict, List, Any

from src.skills.base import BaseSkill, SkillResult, SkillContext
from src.models.manager import get_model_manager
from src.agent.tools import web_search, semantic_scholar_search, extract_paper_content
from src.agent.state import SearchResult


class PaperWritingSkill(BaseSkill):
    """Generate academic papers from research findings."""
    
    name = "paper_writing"
    display_name = "Academic Paper Writer"
    description = "Generate structured academic papers with abstract, introduction, related work, methodology, results, and conclusion sections. Supports research papers, survey papers, and short papers."
    version = "2.0.0"
    author = "CS599 Agent"
    tags = ["writing", "paper", "academic", "latex"]
    
    parameters_schema = {
        "topic": {
            "type": "string",
            "description": "Paper topic or title",
            "required": True,
        },
        "paper_type": {
            "type": "string",
            "description": "Type of paper",
            "options": ["research", "survey", "short", "review"],
            "default": "research",
        },
        "sections": {
            "type": "array",
            "description": "Sections to include",
            "options": ["abstract", "introduction", "related_work", "methodology", 
                       "experiments", "results", "discussion", "conclusion", "references"],
            "default": ["abstract", "introduction", "related_work", "methodology", 
                       "experiments", "conclusion", "references"],
        },
        "length": {
            "type": "string",
            "description": "Paper length",
            "options": ["short", "medium", "long"],
            "default": "medium",
        },
        "style": {
            "type": "string",
            "description": "Writing style",
            "options": ["academic", "ieee", "acm", "apa"],
            "default": "academic",
        },
    }
    
    def execute(self, context: SkillContext) -> SkillResult:
        """Generate academic paper."""
        topic = context.topic
        params = context.custom_params
        paper_type = params.get("paper_type", "research")
        sections = params.get("sections", ["abstract", "introduction", "related_work",
                                          "methodology", "experiments", "conclusion", "references"])
        length = params.get("length", "medium")
        style = params.get("style", "academic")
        steps = []

        try:
            manager = get_model_manager()
            llm = manager.create_llm_client(
                context.provider_name, context.model_id, context.temperature
            )
        except Exception as e:
            return SkillResult(success=False, error=f"LLM 客户端创建失败: {e}")

        try:
            # Step 1: Gather research material
            steps.append({"step": 1, "action": "research", "status": "running"})
            research_data = self._gather_research(topic, steps)
            steps[-1]["status"] = "done"

            # Step 2: Evaluate academic papers using ResearchSkill's evaluation pipeline
            # (composition mode — reuse research_skill's LLM evaluation instead of LLM-fabricated refs)
            evaluated_papers = []
            worth_citing_papers = []
            ss_orig = research_data.get("_ss_orig", [])
            if ss_orig:
                steps.append({"step": 2, "action": "evaluate_papers", "status": "running"})
                try:
                    from src.skills.builtin.research_skill import ResearchSkill
                    rs = ResearchSkill()
                    # Download paper content for SS results
                    for r in ss_orig:
                        content = extract_paper_content(r)
                        r.content = content or (r.snippet[:2000] if r.snippet else "")
                    academic_papers = [r for r in ss_orig if r.content]
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

            # Step 3: Generate each section
            paper_sections = {}
            section_prompts = self._get_section_prompts(style, paper_type, length)

            # Build evaluated sources string for prompts (numbered references)
            if evaluated_papers:
                sources_lines = []
                for idx, ev in enumerate(evaluated_papers, 1):
                    sources_lines.append(f"[{idx}] {ev['title']} — {'✅' if ev.get('worth_citing') else '❌'} {ev.get('relevance', '?')}")
                sources_str = "\n".join(sources_lines)
            else:
                sources_str = "\n".join(f"- {s.get('title', '')}" for s in research_data.get("sources", [])[:15])

            for i, section in enumerate(sections, 3):
                steps.append({"step": i, "action": f"write_{section}", "status": "running"})

                if section in section_prompts:
                    prompt = section_prompts[section]
                    prompt = prompt.replace("TOPIC_PLACEHOLDER", topic)
                    prompt = prompt.replace("SNIPPETS_PLACEHOLDER", research_data.get("snippets", "")[:3000])
                    prompt = prompt.replace("SOURCES_PLACEHOLDER", sources_str)
                    try:
                        response = llm.invoke([{"role": "user", "content": prompt}])
                        content = response.content if hasattr(response, 'content') else str(response)
                        paper_sections[section] = content
                        steps[-1]["status"] = "done"
                        steps[-1]["result"] = f"Generated {len(content)} chars"
                    except Exception as e:
                        paper_sections[section] = f"<!-- Error generating section: {e} -->"
                        steps[-1]["status"] = "error"
                        steps[-1]["error"] = str(e)

            # Step 3: Assemble final paper
            steps.append({"step": len(steps) + 1, "action": "assemble", "status": "running"})
            paper = self._assemble_paper(topic, paper_sections, sections, style)

            # Append real references from evaluated papers (replace LLM-fabricated ones)
            if worth_citing_papers:
                real_refs = "\n\n## References (Verified)\n\n"
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
                    real_refs += ref + "\n\n"
                paper += "\n\n" + real_refs
                paper += "\n*References are real academic papers evaluated by LLM. See also the \"References\" section above.*\n"

            steps[-1]["status"] = "done"

        except Exception as e:
            steps.append({"step": len(steps) + 1, "action": "error", "status": "error", "result": str(e)})
            return SkillResult(success=False, error=f"Paper generation failed: {e}", steps=steps)

        return SkillResult(
            success=True,
            content=paper,
            metadata={
                "paper_type": paper_type,
                "sections": sections,
                "length": length,
                "style": style,
                "num_sections": len(paper_sections),
                "research_sources": len(research_data.get("sources", [])),
            },
            steps=steps,
        )
    
    def _gather_research(self, topic: str, steps: list) -> Dict:
        """Gather research material for the paper."""
        # Keep original SearchResult objects for LLM evaluation
        web_results = web_search(topic, max_results=5)
        ss_results = semantic_scholar_search(topic, max_results=5)
        
        sources = []
        for r in web_results:
            sources.append({"title": r.title, "url": r.url, "type": "web"})
        for r in ss_results:
            sources.append({"title": r.title, "url": r.url, "type": "semantic_scholar"})
        
        snippets = [r.snippet for r in web_results + ss_results if r.snippet]
        
        return {
            "topic": topic,
            "web_results": [r.__dict__ for r in web_results],
            "ss_results": [r.__dict__ for r in ss_results],
            "sources": sources,
            "snippets": "\n".join(snippets[:10]),
            "_web_orig": web_results,
            "_ss_orig": ss_results,
        }
    
    def _get_section_prompts(self, style: str, paper_type: str, length: str) -> Dict[str, str]:
        """Get prompts for each paper section."""
        word_counts = {"short": "300-500", "medium": "500-800", "long": "800-1200"}
        wc = word_counts.get(length, "500-800")
        style_upper = style.upper()

        # NOTE: These are plain strings (NOT f-strings).
        # Placeholders {topic}, {snippets}, {sources} are filled via str.replace() in execute().
        return {
            "abstract": f"""Write an academic abstract ({wc} words) for a {paper_type} paper on: TOPIC_PLACEHOLDER

Research context:
SNIPPETS_PLACEHOLDER

Requirements:
- Background and motivation (2-3 sentences)
- Problem statement (1-2 sentences)
- Proposed approach or key findings (2-3 sentences)
- Significance and implications (1-2 sentences)
- Write in {style_upper} style
- Use formal academic language
- Do not cite references in the abstract

Output only the abstract text, no headings.""",

            "introduction": f"""Write the Introduction section ({wc} words) for a paper on: TOPIC_PLACEHOLDER

Research context:
SNIPPETS_PLACEHOLDER

Requirements:
- Hook: Start with a compelling observation or statistic
- Background: Brief context of the field
- Problem: What gap or challenge does this address?
- Contributions: List 3-4 specific contributions of this work
- Roadmap: Brief overview of paper structure
- Write in {style_upper} style with formal academic language

Output only the introduction text.""",

            "related_work": f"""Write the Related Work section ({wc} words) for a paper on: TOPIC_PLACEHOLDER

Available sources:
SOURCES_PLACEHOLDER

Requirements:
- Organize by themes or categories
- Discuss 4-6 relevant works or research directions
- Highlight differences and limitations of existing approaches
- Position this work in the landscape
- Write in {style_upper} style

Output only the related work text.""",

            "methodology": f"""Write the Methodology section ({wc} words) for a paper on: TOPIC_PLACEHOLDER

Requirements:
- Clearly describe the approach or framework
- Define key concepts and notation
- Explain the workflow or architecture
- Justify design decisions
- Include a description of any algorithms or processes
- Write in {style_upper} style

Output only the methodology text.""",

            "experiments": f"""Write the Experiments/Evaluation section ({wc} words) for a paper on: TOPIC_PLACEHOLDER

Requirements:
- Describe experimental setup
- Define evaluation metrics
- Present hypothetical results with tables or descriptions
- Include analysis of results
- Write in {style_upper} style

Output only the experiments text.""",

            "results": f"""Write the Results section ({wc} words) for a paper on: TOPIC_PLACEHOLDER

Requirements:
- Present key findings clearly
- Use structured descriptions (what would be tables/figures in final paper)
- Compare with baseline approaches
- Highlight significant improvements or observations
- Write in {style_upper} style

Output only the results text.""",

            "discussion": f"""Write the Discussion section ({wc} words) for a paper on: TOPIC_PLACEHOLDER

Requirements:
- Interpret the results
- Discuss implications for the field
- Acknowledge limitations
- Suggest future research directions
- Write in {style_upper} style

Output only the discussion text.""",

            "conclusion": f"""Write the Conclusion section ({wc} words) for a paper on: TOPIC_PLACEHOLDER

Requirements:
- Summarize key contributions and findings
- Restate significance
- Mention limitations briefly
- Suggest future work (2-3 directions)
- End with a forward-looking statement
- Write in {style_upper} style

Output only the conclusion text.""",

            "references": f"""Generate a References section in {style_upper} citation format using ONLY the verified sources listed below.

Available verified sources:
SOURCES_PLACEHOLDER

Requirements:
- Cite ONLY from the available verified sources above
- Use {style_upper} citation format
- Do NOT invent or fabricate any references
- If sources are insufficient, state that clearly
- Include journal/conference information where available

Output only the references in proper format.""",
        }
    
    def _assemble_paper(self, topic: str, sections: Dict[str, str], 
                        section_order: List[str], style: str) -> str:
        """Assemble paper sections into final document."""
        style_headers = {
            "ieee": "IEEE Format",
            "acm": "ACM Format", 
            "apa": "APA Format",
            "academic": "Academic Paper",
        }
        
        header = style_headers.get(style, "Academic Paper")
        
        paper = f"""% {topic}
% Academic Paper
% Generated by CS599 AI Research Agent

---
title: "{topic}"
documentclass: article
---

"""
        
        section_titles = {
            "abstract": "## Abstract",
            "introduction": "## 1. Introduction",
            "related_work": "## 2. Related Work",
            "methodology": "## 3. Methodology",
            "experiments": "## 4. Experiments",
            "results": "## 5. Results",
            "discussion": "## 6. Discussion",
            "conclusion": "## 7. Conclusion",
            "references": "## References",
        }
        
        for section in section_order:
            if section in sections:
                title = section_titles.get(section, f"## {section.replace('_', ' ').title()}")
                paper += f"\n{title}\n\n{sections[section]}\n\n---\n"
        
        paper += """
---

*This paper was generated by CS599 AI Research Agent. The content should be reviewed and verified by the author before submission.*
"""
        return paper
