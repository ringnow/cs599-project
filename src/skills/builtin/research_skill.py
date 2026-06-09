"""Research Skill - Automated topic research with multi-source search.

This is the foundational skill that performs deep research on a given topic
by decomposing it into sub-questions, searching the web and academic databases,
and synthesizing findings into a comprehensive report.
"""
import json
import re
import time
from typing import Dict, List, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.skills.base import BaseSkill, SkillResult, SkillContext
from src.models.manager import get_model_manager
from src.agent.tools import web_search, semantic_scholar_search, extract_web_content, extract_paper_content
from src.agent.state import SearchResult
from src.agent.image_gen import generate_image, enhance_report_with_images, embed_images_in_markdown
from src.api.cancel import is_cancelled


class ResearchSkill(BaseSkill):
    """Deep research skill with multi-source information gathering."""

    name = "research"
    display_name = "Deep Research"
    description = "Perform comprehensive research on any topic using web search and academic sources. Decomposes the topic into sub-questions, gathers evidence, and synthesizes a detailed report with sources."
    version = "2.0.0"
    author = "CS599 Agent"
    tags = ["research", "search", "analysis", "foundation"]

    parameters_schema = {
        "topic": {"type": "string", "description": "Research topic or question", "required": True},
        "depth": {"type": "integer", "description": "Research depth (1-5)", "default": 3, "min": 1, "max": 5},
        "sources": {"type": "array", "description": "Sources to use", "options": ["web", "semantic_scholar"], "default": ["web", "semantic_scholar"]},
    }

    def execute(self, context: SkillContext) -> SkillResult:
        """Execute deep research."""
        topic = context.topic
        depth = context.custom_params.get("depth", 3)
        sources = context.custom_params.get("sources", ["web", "semantic_scholar"])
        request_id = context.custom_params.get("request_id", "")
        steps = []
        all_results = []
        all_extracted = []

        try:
            manager = get_model_manager()
            llm = manager.create_llm_client(
                context.provider_name, context.model_id, context.temperature
            )
        except Exception as e:
            return SkillResult(success=False, error=f"LLM client creation failed: {e}")

        try:
            # Step 1: Decompose topic
            steps.append({"step": 1, "action": "decompose", "status": "running"})
            sub_questions = self._decompose_topic(llm, topic, depth)
            steps[-1]["status"] = "done"
            steps[-1]["result"] = f"Generated {len(sub_questions)} sub-questions"

            # Step 2: Research (search + extract + synthesise) ALL sub-questions
            # in parallel.  Each thread creates its own ChatOpenAI so there is
            # NO shared mutable state across threads (no ModelManager calls).
            # Extract provider credentials once in the main thread first.
            _api_key = ""
            _base_url = ""
            _model_id = context.model_id
            try:
                p = manager.get_provider(context.provider_name)
                if p:
                    _api_key = p.api_key
                    _base_url = p.config.base_url
                    _model_id = context.model_id or p.config.default_model or "deepseek-chat"
            except Exception:
                pass

            syntheses = []
            all_evaluated = []  # Collect evaluated papers from all threads
            with ThreadPoolExecutor(max_workers=min(len(sub_questions), 3)) as executor:
                future_map = {}
                for i, question in enumerate(sub_questions):
                    step_info = {"step": i + 2, "action": "research", "query": question, "status": "running"}
                    steps.append(step_info)
                    future = executor.submit(
                        self._research_single, question, sources, depth, request_id,
                        _api_key, _base_url, _model_id,
                    )
                    future_map[future] = (i, step_info)

                for future in as_completed(future_map):
                    i, step_info = future_map[future]
                    try:
                        q, sr, summary, ev_papers = future.result()
                        all_results.extend(sr)
                        all_evaluated.extend(ev_papers)
                        if summary:
                            syntheses.append({"question": q, "summary": summary})
                            step_info["status"] = "done"
                            step_info["result"] = f"Found {len(sr)} sources → synthesized"
                        else:
                            step_info["status"] = "warning"
                            step_info["result"] = "No results found"
                    except Exception as e:
                        step_info["status"] = "error"
                        step_info["result"] = str(e)

            # Step 3: Generate final report (main thread, uses original `llm`)
            # Filter out failed syntheses (timeout / error) so the LLM doesn't
            # regurgitate error messages into the final report.
            if request_id and is_cancelled(request_id):
                return SkillResult(
                    success=False,
                    content="任务已被用户取消。",
                    steps=steps,
                )

            valid_syntheses = [
                s for s in syntheses
                if not s["summary"].startswith("Error during synthesis")
                and not s["summary"].startswith("Request timed out")
            ]
            if not valid_syntheses and syntheses:
                # All failed — use raw excerpts as last resort
                valid_syntheses = syntheses[:1]

            # Build sources list ONLY from evaluated academic papers (not web content)
            worth_citing = [ev for ev in all_evaluated if ev.get("worth_citing")]
            sources_list = []
            for ev in worth_citing:
                entry = {
                    "title": ev["title"],
                    "url": ev.get("url", ""),
                    "source": "semantic_scholar",
                    "ref_num": ev.get("ref_num", len(sources_list) + 1),
                    "authors": ev.get("authors", []),
                    "year": ev.get("year", 0),
                    "journal": ev.get("journal", ""),
                    "key_findings": ev.get("key_findings", ""),
                    "relevance": ev.get("relevance", ""),
                    "worth_citing": True,
                }
                sources_list.append(entry)

            # If no academic papers passed evaluation, include them all as last resort
            if not sources_list:
                for ev in all_evaluated:
                    sources_list.append({
                        "title": ev["title"],
                        "url": ev.get("url", ""),
                        "source": "semantic_scholar",
                        "ref_num": ev.get("ref_num", len(sources_list) + 1),
                        "authors": ev.get("authors", []),
                        "year": ev.get("year", 0),
                        "journal": ev.get("journal", ""),
                        "key_findings": ev.get("key_findings", ""),
                        "relevance": ev.get("relevance", "低"),
                        "worth_citing": False,
                    })

            steps.append({"step": len(steps) + 1, "action": "report", "status": "running"})
            report = self._generate_report(llm, topic, sub_questions, valid_syntheses, sources_list)
            steps[-1]["status"] = "done"

            # Step 4: Generate images for the report (post-processing)
            generated_images = []
            try:
                steps.append({"step": len(steps) + 1, "action": "image_gen", "status": "running"})
                generated_images = enhance_report_with_images(
                    report, llm,
                    max_images=2,  # Limit to 2 images per report
                )
                success_count = sum(1 for img in generated_images if img.get("success"))
                if success_count > 0:
                    # Inject image references into report markdown
                    report = embed_images_in_markdown(report, generated_images)
                    steps[-1]["status"] = "done"
                    steps[-1]["result"] = f"Generated {success_count} images"
                else:
                    steps[-1]["status"] = "warning"
                    steps[-1]["result"] = "No images generated"
            except Exception as img_e:
                steps[-1]["status"] = "warning"
                steps[-1]["result"] = f"Image generation skipped: {img_e}"

            return SkillResult(
                success=True,
                content=report,
                metadata={
                    "sub_questions": sub_questions,
                    "num_sources": len(all_results),
                    "num_papers_read": len(all_evaluated),
                    "num_papers_cited": len(sources_list),
                    "depth": depth,
                    "generated_images": generated_images,
                },
                steps=steps,
                sources=sources_list,
            )

        except Exception as e:
            steps.append({"step": len(steps) + 1, "action": "error", "status": "error", "result": str(e)})
            return SkillResult(success=False, error=f"Research failed: {e}", steps=steps)

    def _research_single(self, question: str, sources: List[str], depth: int,
                          request_id: str, api_key: str, base_url: str, model_id: str):
        """Search + READ PAPERS + extract + evaluate + synthesise ONE sub-question.

        Key improvements over old version:
        1. Web search for background context (not cited as formal references)
        2. Semantic Scholar for academic papers (下载PDF/API获取全文)
        3. LLM evaluates each paper's relevance and decides worth_citing
        4. Only evaluated papers are synthesized and returned as potential references
        5. Web content used as supplementary background ONLY

        Returns (question, all_search_results, summary_text, evaluated_papers).
        - all_search_results: ALL results (web + academic) for tracking
        - evaluated_papers: ONLY academic papers that passed LLM evaluation
        """
        if request_id and is_cancelled(request_id):
            return question, [], "", []

        search_results = []

        # ---- Web search (background context only, not formal references) ----
        if "web" in sources:
            web_results = web_search(question, max_results=3 + depth)
            search_results.extend(web_results)
            if web_results:
                print(f"  → 网络来源: {len(web_results)} 条（仅做背景参考）")

        # ---- Academic search via Semantic Scholar ----
        if "semantic_scholar" in sources:
            en_query = question
            if api_key and base_url and model_id:
                try:
                    from langchain_openai import ChatOpenAI
                    tllm = ChatOpenAI(
                        model=model_id, api_key=api_key, base_url=base_url,
                        temperature=0, timeout=15, max_retries=0,
                    )
                    tr = tllm.invoke([{"role": "user",
                        "content": f"Extract 5-8 key search terms in English for academic paper search from this query. Only output the terms, comma-separated on one line, no explanation.\nQuery: {question}"}])
                    translated = tr.content if hasattr(tr, 'content') else str(tr)
                    if translated and len(translated) < 300:
                        en_query = translated.strip()
                        print(f"  → 关键词: '{en_query[:80]}...'")
                except Exception:
                    pass

            results = semantic_scholar_search(en_query, max_results=4)
            search_results.extend(results)
            if results:
                print(f"  → 学术来源: Semantic Scholar ({len(results)} 篇论文)")

        # ---- Read paper content (download PDF or API fetch) ----
        for r in search_results:
            if r.source == "semantic_scholar":
                print(f"  📖 正在阅读论文: {r.title[:60]}...")
                content = extract_paper_content(r)
                if content:
                    r.content = content
                    print(f"     ✓ 获取到 {len(content)} 字内容")
                else:
                    print(f"     ⚠️ 未能获取论文内容")
                    r.content = r.snippet[:2000] if r.snippet else ""

        # ---- Evaluate academic papers with LLM ----
        academic_papers = [r for r in search_results if r.source == "semantic_scholar" and r.content]
        evaluated_papers = []
        paper_evaluations = []
        if academic_papers and api_key and base_url and model_id:
            try:
                from langchain_openai import ChatOpenAI
                eval_llm = ChatOpenAI(
                    model=model_id, api_key=api_key, base_url=base_url,
                    temperature=0.3, timeout=60, max_retries=0,
                )
                paper_evaluations = self._evaluate_papers(eval_llm, academic_papers, question)
                for ev in paper_evaluations:
                    icon = "✅" if ev.get("worth_citing") else "❌"
                    print(f"  📊 论文评估 [{ev.get('ref_num','?')}]: {ev.get('title','')[:40]}... → {ev.get('relevance','?')} {icon}")
            except Exception as e:
                print(f"  ⚠️ 论文评估失败: {e}")

        # ---- Build synthesis input ----
        # Web content: used as background context, NOT as formal references
        extracted = []
        web_count = 0
        for r in search_results:
            if r.source == "web" and r.url:
                if web_count < 2:  # Limit web context to 2 sources
                    content = extract_web_content(r.url)
                    if content:
                        extracted.append(f"[背景信息] {r.title}: {content[:1500]}")
                        web_count += 1

        # Academic papers: only include those evaluated as worth_citing
        for ev in paper_evaluations:
            paper = ev.get("_paper")
            if paper and paper.content and ev.get("worth_citing"):
                ref_num = ev.get("ref_num", "?")
                key_findings = ev.get("key_findings", "")
                extracted.append(
                    f"[学术论文 #{ref_num}] {paper.title} ({paper.year})\n"
                    f"  核心发现: {key_findings}\n"
                    f"  原文摘要: {paper.content[:2000]}"
                )
                evaluated_papers.append(ev)

        # Fallback: if no evaluated papers, still use abstracts
        if not evaluated_papers:
            for r in search_results:
                if r.source == "semantic_scholar":
                    extracted.append(f"[学术论文] {r.title}\n摘要: {r.snippet[:1500]}")
                    # Create a basic evaluation for tracking
                    if r.content:
                        evaluated_papers.append({
                            "ref_num": len(evaluated_papers) + 1,
                            "title": r.title,
                            "authors": r.authors or [],
                            "year": r.year,
                            "journal": r.journal,
                            "url": r.url,
                            "key_findings": "",
                            "relevance": "低",
                            "worth_citing": True,  # Include as last resort
                            "reason": "LLM评估不可用，作为后备引用",
                            "_paper": r,
                        })

        # ---- Synthesize ----
        summary = ""
        if extracted and api_key and base_url and model_id:
            try:
                from langchain_openai import ChatOpenAI
                thread_llm = ChatOpenAI(
                    model=model_id,
                    api_key=api_key,
                    base_url=base_url,
                    temperature=0.7,
                    timeout=120,
                    max_retries=0,
                )
                summary = self._synthesize(thread_llm, question, extracted, evaluated_papers)
            except Exception:
                summary = "\n\n".join(extracted[:3])[:1500]

        return question, search_results, summary, evaluated_papers

    def _decompose_topic(self, llm, topic: str, depth: int) -> List[str]:
        """Decompose topic into sub-questions."""
        prompt = f"""Break down this research topic into {depth + 1} specific sub-questions.

Topic: {topic}

Requirements:
- Each sub-question should be specific and researchable
- Cover different aspects (definition, history, current approaches, challenges, future)
- Respond ONLY with a JSON array of strings

Example: ["What is X and how did it originate?", "What are the main approaches to X?", ...]"""

        try:
            response = llm.invoke([{"role": "user", "content": prompt}])
            content = response.content if hasattr(response, 'content') else str(response)

            match = re.search(r'\[.*?\]', content, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception:
            pass

        return [
            f"What is {topic}?",
            f"What are the key developments in {topic}?",
            f"What are the current challenges and future directions for {topic}?"
        ]

    def _evaluate_papers(self, llm, papers: List[SearchResult], topic: str) -> List[Dict]:
        """Evaluate each paper's relevance and extract key findings.

        For each paper, the LLM reads the full content and determines:
        - Core problem / method / findings
        - Relevance to the research topic (高/中/低)
        - Whether it's worth citing
        - Key findings that could be used in the report

        Args:
            llm: ChatOpenAI instance
            papers: List of SearchResult with .content populated
            topic: Research sub-question

        Returns:
            List of evaluation dicts with keys: ref_num, title, key_findings,
            relevance, worth_citing, _paper
        """
        evaluations = []
        for idx, paper in enumerate(papers, 1):
            if not paper.content:
                evaluations.append({
                    "ref_num": idx,
                    "title": paper.title,
                    "authors": paper.authors or [],
                    "year": paper.year,
                    "journal": paper.journal,
                    "url": paper.url,
                    "key_findings": "（无可用内容）",
                    "relevance": "unknown",
                    "worth_citing": False,
                    "reason": "论文内容不可获取",
                    "_paper": paper,
                })
                continue

            prompt = f"""你是一名学术审稿人。以下是一篇学术论文的完整内容，以及当前正在研究的主题。

研究主题：{topic}

论文标题：{paper.title}
作者：{', '.join(paper.authors[:5]) if paper.authors else '未知'}
发表年份：{paper.year}
引用数：{paper.citation_count}
期刊/会议：{paper.journal}

论文内容（前4000字）：
{paper.content[:4000]}

请仔细阅读以上论文内容，然后回答以下问题（JSON格式）：

{{
  "key_findings": "这篇论文的核心发现/方法/结论（100-200字中文）",
  "relevance": "论文与本研究的关联度：高/中/低",
  "worth_citing": true/false,
  "reason": "判断理由（50字中文）",
  "usable_quotes": "可以从论文中直接引用的具体观点或数据（50-100字）"
}}

只输出JSON，不要其他文字。"""

            try:
                response = llm.invoke([{"role": "user", "content": prompt}])
                raw = response.content if hasattr(response, 'content') else str(response)
                # Extract JSON from response
                import re as _re
                m = _re.search(r'\{.*\}', raw, _re.DOTALL)
                if m:
                    result = json.loads(m.group())
                else:
                    result = {"key_findings": raw[:200], "relevance": "低", "worth_citing": False, "reason": "解析失败", "usable_quotes": ""}

                result["ref_num"] = idx
                result["title"] = paper.title
                result["authors"] = paper.authors or []
                result["year"] = paper.year
                result["journal"] = paper.journal
                result["url"] = paper.url
                result["_paper"] = paper
                evaluations.append(result)
                print(f"  📋 论文 #{idx} 评估完成: {result.get('relevance','?')} {'✅' if result.get('worth_citing') else '❌'}")
            except Exception as e:
                evaluations.append({
                    "ref_num": idx,
                    "title": paper.title,
                    "key_findings": f"评估失败: {e}",
                    "relevance": "低",
                    "worth_citing": False,
                    "reason": f"LLM评估异常: {e}",
                    "_paper": paper,
                })

        return evaluations

    def _synthesize(self, llm, question: str, excerpts: List[str],
                    evaluated_papers: List[Dict] = None) -> str:
        """Synthesize findings for a sub-question.

        Uses evaluated papers with [N] numbering to ensure consistent citations.
        Only academic papers (not web content) are assigned reference numbers.
        """
        # Build reference index from evaluated academic papers ONLY
        ref_section = ""
        if evaluated_papers:
            ref_lines = []
            for ev in evaluated_papers:
                if ev.get("worth_citing"):
                    authors_str = ", ".join(ev["authors"][:3]) if ev.get("authors") else ""
                    ref_lines.append(
                        f"[{ev['ref_num']}] {ev['title']}. "
                        f"{authors_str}{' (' + str(ev['year']) + ')' if ev.get('year') else ''}"
                        f"{'. ' + ev['journal'] if ev.get('journal') else ''}"
                    )
            if ref_lines:
                ref_section = "学术文献编号：\n" + "\n".join(ref_lines)
            else:
                ref_section = "（无符合引用标准的学术文献）"

        content_text = "\n\n---\n\n".join(excerpts[-5:])

        prompt = f"""基于以下研究摘录和学术文献回答问题。

研究问题：{question}

{ref_section}

研究摘录内容（含背景信息和学术论文摘要）：
{content_text}

写作要求：
1. **只使用摘录中提供的信息**，不要添加任何摘录中没有的内容
2. 在回答中引用学术文献时，**必须使用 [编号] 格式**（如 [1]、[2]）
3. [编号] 与上方"学术文献编号"中的编号一一对应
4. "背景信息"类的网络内容仅供参考，不作为学术引用
5. 如果摘录不足以完整回答问题，明确指出哪些部分缺乏依据

请提供详细回答（300-500字）："""

        try:
            response = llm.invoke([{"role": "user", "content": prompt}])
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            return f"Error during synthesis: {e}"

    def _generate_report(self, llm, topic: str, sub_questions: List[str],
                         syntheses: List[Dict], sources_list: List[Dict]) -> str:
        """Generate final research report with evaluated and verified references.

        Follows research-writing-skill standards:
        - IMRaD structure (Abstract→Introduction→Related Work→Methodology→
          Experiments→Results and Discussion→Conclusion)
        - Writing principles: no fabricated data, separate source types,
          avoid vague terms
        - Editorial principles: Claim-First headings, Problem-First,
          Technical claims require citations

        Only academic papers (from Semantic Scholar) that passed LLM evaluation
        are included. CSDN、知乎等非学术网络内容不作为正式引用.
        References use proper academic format with authors, year, journal.
        """
        syntheses_text = "\n\n---\n\n".join(
            f"### {s['question']}\n\n{s['summary']}" for s in syntheses
        )

        # Build reference list from evaluated academic papers ONLY
        ref_lines = []
        for i, s in enumerate(sources_list, 1):
            title = s.get('title', 'Untitled')

            # Format authors properly
            authors = s.get('authors', [])
            authors_str = ""
            if authors and isinstance(authors, list):
                author_names = [a if isinstance(a, str) else a.get('name', '') for a in authors if a]
                if author_names:
                    author_names = [n for n in author_names if n]
                    if len(author_names) == 1:
                        authors_str = f"{author_names[0]}."
                    elif len(author_names) <= 3:
                        authors_str = ", ".join(author_names) + "."
                    else:
                        authors_str = ", ".join(author_names[:3]) + ", et al."

            year = s.get('year', '')
            journal = s.get('journal', '')
            url = s.get('url', '')

            # Build proper academic reference
            ref_str = f"[{i}]"
            if authors_str:
                ref_str += f" {authors_str}"
            ref_str += f" {title}"
            if year:
                ref_str += f" ({year})"
            if journal:
                ref_str += f". {journal}"
            if url:
                ref_str += f". {url}"

            ref_lines.append(ref_str)

        real_refs = "\n".join(ref_lines) if ref_lines else "（搜索未返回有效的学术文献）"

        # Build compact reference table for LLM
        ref_table_lines = []
        for i, s in enumerate(sources_list, 1):
            ref_table_lines.append(f"[{i}] {s.get('title', 'Untitled')}")
        ref_table = "\n".join(ref_table_lines)

        prompt = f"""You are an academic researcher writing a survey/review paper. Write the report in **English** following the standard IMRaD (Introduction, Methods, Results, and Discussion) structure.

## Research Topic
{topic}

## Verified Academic References (all papers have been read and evaluated)
{real_refs}

## Reference Number Lookup Table
{ref_table}

## Sub-Question Research Syntheses (already contain [N] citations to the references above)
{syntheses_text}

---

### Writing Principles (strictly follow these)

1. **NO fabricated data**: Do NOT invent any numerical results, DOI numbers, journal volumes/pages, or experimental outcomes that are not present in the provided materials.
2. **Source-type labeling**: Clearly distinguish three categories of information:
   - **Original/sourced** — facts, findings, or quotes directly from the provided academic papers
   - **Inferred/synthesized** — reasonable conclusions drawn across multiple sources (label as "this suggests that...")
   - **Suggested/extended** — speculative future directions or hypothetical applications (label as "one possible extension could be...")
3. **NO vague promotional language**: Avoid terms like "significant", "state-of-the-art", "advanced", "effective", "promising", "novel", "groundbreaking" unless they are DIRECTLY supported by a cited source. Instead, use measurable or comparative phrasing (e.g., "achieved 94.2% accuracy on Dataset X [1]").
4. **Every technical claim requires a citation**: Any statement about a method, algorithm, performance metric, or phenomenon MUST be followed by a [N] reference.
5. **Cite only from the Reference Number Lookup Table above**: Do NOT cite any paper not in this list. Do NOT cite web pages (CSDN, Zhihu, blog posts, etc.).
6. **When literature is insufficient**: If a particular aspect is not covered by the available references, clearly state "The reviewed literature does not provide sufficient evidence for..." rather than fabricating content.
7. **First-person perspective**: Write as the reviewing author ("we find that...", "the reviewed studies indicate..."), not as the original authors of cited papers.

---

### Section Structure and Rhetorical Guides

Write the report with the following sections:

#### 1. Abstract
(~150 words) One paragraph covering: research problem → approach/method → key findings → main contribution.

#### 2. Introduction
Structure: background of the problem → unresolved challenge or gap → why this gap matters → what this review does → key contributions.
- Every statement describing the problem domain must be supported by [N].
- End with a clear statement of contributions.

#### 3. Related Work
Organize by technical theme or approach, not by paper. For each theme:
- Compare and contrast assumptions, methodologies, and limitations across papers.
- Use Claim-First headings (e.g., "Deep Learning Methods for Time-Series Forecasting" not "Related Work in Time-Series").

#### 4. Methodology / Approach
Describe the scope, inclusion criteria, and analytical framework of this review:
- Search strategy and databases used
- Inclusion/exclusion criteria for papers
- Quality assessment method (papers evaluated by LLM for relevance)
- Synthesis method

#### 5. Results and Discussion
Structure each finding as: **Claim first** → evidence from [N] sources → mechanism/explanation → limitations.
- Use Claim-First subheadings (e.g., "Transformer-Based Models Outperform RNNs on Long-Sequence Tasks" not "Results for Transformer Models").
- Discuss disagreements or contradictions between sources.
- Explicitly note when a finding comes from a single source vs. multiple corroborating sources.

#### 6. Conclusion
- Summarize the answer to the research question
- Recap the main evidence
- Acknowledge limitations of this review
- Suggest directions for future research

---

### Output Format
Write in Markdown. Start with the title as H1. Use H2 for sections (## Abstract, ## Introduction, etc.) and H3 for subsections."""

        try:
            response = llm.invoke([{"role": "user", "content": prompt}])
            content = response.content if hasattr(response, 'content') else str(response)
            # Append REAL references (not LLM-generated fakes)
            if real_refs:
                content += "\n\n## References\n" + real_refs
            content += "\n\n---\n*This report cites only peer-reviewed academic papers that were fully read and evaluated for relevance. Literature search powered by [Semantic Scholar](https://www.semanticscholar.org/).*"
            return content
        except Exception as e:
            return f"# {topic}\n\n## Error\n{e}\n\n## Raw Findings\n\n{syntheses_text}"
