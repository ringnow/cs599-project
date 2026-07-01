"""Query optimizer — Query Rewriting, HyDE, and Multi-Query expansion.

These techniques transform the user's raw query into more effective
retrieval queries, dramatically improving recall.
"""
import os
import json
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

# Level of optimization to apply: "off" | "rewrite" | "hyde" | "multi"
OPT_LEVEL = os.getenv("RAG_QUERY_OPTIMIZATION", "rewrite").strip().lower()


def _get_llm():
    """Get the default LLM client for query optimization."""
    from src.models.manager import get_model_manager
    from src.api.dependencies import resolve_provider_model
    provider, model = resolve_provider_model()
    mgr = get_model_manager()
    return mgr.create_llm_client(provider, model, temperature=0.3)


# ── Query Rewriting ────────────────────────────────────────────────────

def rewrite_query(original: str) -> str:
    """Rewrite a vague/short query into a more precise retrieval query.

    Example:
        "transformer 进展" → "transformer 架构最新进展 2026 年研究综述"
    """
    prompt = f"""你是一个检索查询优化专家。请将用户的模糊查询改写为更精确、更适合向量检索的查询。

要求：
- 保持原意，但补充相关关键词和同义词
- 移除口语化表达，改为书面学术风格
- 直接输出改写后的查询文本，不要解释

原始查询：{original}

改写后的查询："""
    try:
        llm = _get_llm()
        resp = llm.invoke([{"role": "user", "content": prompt}])
        rewritten = resp.content.strip() if hasattr(resp, "content") else str(resp).strip()
        # Remove quotes if LLM wrapped in them
        rewritten = rewritten.strip('"').strip("'")
        logger.info("Query rewritten: %r → %r", original[:50], rewritten[:80])
        return rewritten
    except Exception as e:
        logger.warning("Query rewriting failed: %s", e)
        return original


# ── HyDE: Hypothetical Document Embeddings ─────────────────────────────

def hyde_generate(original: str) -> str:
    """Generate a hypothetical ideal document for the query.

    The generated text is used for embedding-based retrieval instead of
    the raw query, because in embedding space the hypothetical document
    is often closer to relevant documents than the short query.
    """
    prompt = f"""你是一个学术写作专家。请根据以下查询，撰写一段假设的理想文档段落。
这段文档应该是你在知识库中期望找到的内容，包含具体的术语、概念和细节。

请用中文撰写，2-3 个段落，直接输出文档内容。

查询：{original}

假设的理想文档段落："""
    try:
        llm = _get_llm()
        resp = llm.invoke([{"role": "user", "content": prompt}])
        hyde_text = resp.content.strip() if hasattr(resp, "content") else str(resp).strip()
        logger.info("HyDE generated (%d chars) for: %r", len(hyde_text), original[:50])
        return hyde_text
    except Exception as e:
        logger.warning("HyDE generation failed: %s", e)
        return original


# ── Multi-Query Expansion ──────────────────────────────────────────────

def expand_queries(original: str, num_queries: int = 3) -> List[str]:
    """Expand one query into multiple queries from different angles."""
    prompt = f"""你是一个检索专家。请将以下用户查询扩展为 {num_queries} 个不同角度的子查询。
每个子查询应关注不同的方面或使用不同的措辞，以提高检索召回率。

请每行一个，直接输出 {num_queries} 个子查询，不要编号。

原始查询：{original}

{num_queries} 个子查询："""
    try:
        llm = _get_llm()
        resp = llm.invoke([{"role": "user", "content": prompt}])
        text = resp.content.strip() if hasattr(resp, "content") else str(resp).strip()
        lines = [line.strip().strip('"').strip("'").lstrip("0123456789.、- ") for line in text.split("\n") if line.strip()]
        queries = [line for line in lines if len(line) > 5][:num_queries]
        if not queries:
            queries = [original]
        logger.info("Query expanded: 1 → %d queries for: %r", len(queries), original[:50])
        return queries
    except Exception as e:
        logger.warning("Query expansion failed: %s", e)
        return [original]


# ── Unified API ────────────────────────────────────────────────────────

def optimize_query(original: str) -> List[str]:
    """Apply configured query optimization level.

    Returns a list of query strings to search with.
    """
    if not original or not original.strip():
        return [original]

    level = OPT_LEVEL

    if level == "off":
        return [original]

    if level == "rewrite":
        rewritten = rewrite_query(original)
        return [rewritten]

    if level == "hyde":
        # HyDE uses the hypothetical doc as the search query
        hyde_doc = hyde_generate(original)
        return [hyde_doc]

    if level == "multi":
        # Multi-query: use original + expanded queries
        expanded = expand_queries(original)
        all_queries = [original] + expanded
        return all_queries

    # Default: rewrite only
    rewritten = rewrite_query(original)
    return [rewritten]