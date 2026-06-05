"""Research Skill - Automated topic research with multi-source search.

This is the foundational skill that performs deep research on a given topic
by decomposing it into sub-questions, searching the web and academic databases,
and synthesizing findings into a comprehensive report.
"""
import json
import re
from typing import Dict, List, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.skills.base import BaseSkill, SkillResult, SkillContext
from src.models.manager import get_model_manager
from src.agent.tools import web_search, semantic_scholar_search, extract_web_content
from src.agent.state import SearchResult
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
                        q, sr, summary = future.result()
                        all_results.extend(sr)
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

            steps.append({"step": len(steps) + 1, "action": "report", "status": "running"})
            report = self._generate_report(llm, topic, sub_questions, valid_syntheses)
            steps[-1]["status"] = "done"

            # Collect sources
            sources_list = [
                {"title": r.title, "url": r.url, "source": r.source}
                for r in all_results if r.url
            ]

            return SkillResult(
                success=True,
                content=report,
                metadata={
                    "sub_questions": sub_questions,
                    "num_sources": len(all_results),
                    "num_excerpts": len(all_extracted),
                    "depth": depth,
                },
                steps=steps,
                sources=sources_list,
            )

        except Exception as e:
            steps.append({"step": len(steps) + 1, "action": "error", "status": "error", "result": str(e)})
            return SkillResult(success=False, error=f"Research failed: {e}", steps=steps)

    def _research_single(self, question: str, sources: List[str], depth: int,
                          request_id: str, api_key: str, base_url: str, model_id: str):
        """Search + extract + synthesise ONE sub-question in a thread.

        Each invocation creates its own ChatOpenAI instance so it can safely
        run inside a ``ThreadPoolExecutor`` without touching ModelManager.
        Returns (question, search_results, summary_text).
        """
        if request_id and is_cancelled(request_id):
            return question, [], ""

        search_results = []
        if "web" in sources:
            search_results.extend(web_search(question, max_results=3 + depth))
        # 学术搜索使用 Semantic Scholar
        if "semantic_scholar" in sources:
            results = semantic_scholar_search(question, max_results=4)
            search_results.extend(results)
            if results:
                print(f"  → 学术来源: Semantic Scholar ({len(results)} 篇论文)")

        extracted = []
        for r in search_results[:1]:
            if r.url and r.source == "web":
                content = extract_web_content(r.url)
                if content:
                    extracted.append(f"From {r.title}: {content[:2000]}")
        for r in search_results:
            if r.source == "semantic_scholar":
                extracted.append(f"[Semantic Scholar Paper] {r.title}\nAbstract: {r.snippet[:1500]}")

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
                summary = self._synthesize(thread_llm, question, extracted)
            except Exception:
                summary = "\n\n".join(extracted[:3])[:1500]

        return question, search_results, summary
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

    def _synthesize(self, llm, question: str, excerpts: List[str]) -> str:
        """Synthesize findings for a sub-question."""
        content_text = "\n\n---\n\n".join(excerpts[-5:])

        prompt = f"""基于以下研究摘录回答问题。请严格遵守：
1. **只使用摘录中提供的信息**，不要添加任何摘录中没有的内容
2. 如果摘录不足以完整回答问题，明确指出哪些部分缺乏依据
3. 在回答中引用具体摘录来源

Question: {question}

Excerpts:
{content_text}

请提供详细回答（300-500字）："""

        try:
            response = llm.invoke([{"role": "user", "content": prompt}])
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            return f"Error during synthesis: {e}"

    def _generate_report(self, llm, topic: str, sub_questions: List[str],
                         syntheses: List[Dict]) -> str:
        """Generate final research report."""
        syntheses_text = "\n\n---\n\n".join(
            f"### {s['question']}\n\n{s['summary']}" for s in syntheses
        )

        prompt = f"""基于以下研究结果生成一份专业的学术调研报告。请严格遵守：

1. **只使用下方"Research findings"中提供的信息**，不要编造任何数据、论文标题、作者或结论
2. 如果某个方面没有足够的信息，如实说明"现有资料不足以覆盖该方面"
3. 所有引用必须来自下方的 findings，不得虚构参考文献
4. 在 References 部分只列出实际在报告中引用的来源

研究主题：{topic}

Research findings:
{syntheses_text}

请以 Markdown 格式生成报告，包含以下章节：

# {topic}

## 执行摘要
简要概述（200字左右）

## 引言
背景与重要性

## 核心发现
按主题组织详细发现

## 分析
批判性分析

## 结论
总结与启示

## 参考文献"""

        try:
            response = llm.invoke([{"role": "user", "content": prompt}])
            content = response.content if hasattr(response, 'content') else str(response)
            # Append Semantic Scholar citation when academic search is used
            content += "\n\n---\n*文献检索由 [Semantic Scholar](https://www.semanticscholar.org/) 提供支持。*"
            return content
        except Exception as e:
            return f"# {topic}\n\n## Error\n{e}\n\n## Raw Findings\n\n{syntheses_text}"
