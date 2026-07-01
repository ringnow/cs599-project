"""RAG retriever — hybrid search + query optimization + local-vs-online strategy.

Strategy:
  1. Optionally optimize the query (rewrite / HyDE / multi-query).
  2. Hybrid search: vector + BM25 + rerank.
  3. If enough high-quality hits are found, return them as context.
  4. If not enough good hits, signal that online search is needed.
"""
import os
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Minimum cosine similarity score to consider a hit "relevant".
RELEVANCE_THRESHOLD = float(os.getenv("RAG_RELEVANCE_THRESHOLD", "0.65"))
# Minimum number of good hits needed to skip online search.
MIN_GOOD_HITS = int(os.getenv("RAG_MIN_GOOD_HITS", "3"))
# Whether to use hybrid search (BM25 + vector + rerank)
USE_HYBRID = os.getenv("RAG_USE_HYBRID", "true").strip().lower() == "true"
# Query optimization level: "off" | "rewrite" | "hyde" | "multi"
QUERY_OPT = os.getenv("RAG_QUERY_OPTIMIZATION", "rewrite").strip().lower()


def retrieve(
    query: str,
    top_k: int = 5,
    username: Optional[str] = None,
    doc_type: Optional[str] = None,
) -> Dict:
    """Try local knowledge base first with hybrid search + query optimization.

    Args:
        query: The search query / topic.
        top_k: Max results from vector store.
        username: Filter to user's documents.
        doc_type: Filter by document type.

    Returns:
        {
            "local_results": [{"text", "score", "metadata"}],
            "need_online": bool,
            "context_text": str,
            "total_hits": int,
            "good_hits": int,
            "query_used": str,
            "search_mode": str,
        }
    """
    # 1. Query optimization
    queries_to_search = [query]
    search_mode = "direct"

    if QUERY_OPT != "off":
        try:
            from src.rag.query_optimizer import optimize_query
            optimized = optimize_query(query)
            if optimized and optimized[0] != query:
                logger.info("Query optimization: %r → %r", query[:60], optimized[0][:80])
                queries_to_search = optimized
                search_mode = QUERY_OPT
        except Exception as e:
            logger.debug("Query optimization skipped: %s", e)

    # 2. Search with each query and merge results
    all_hits = []
    seen_ids = set()

    for q in queries_to_search:
        if USE_HYBRID:
            try:
                from src.rag.hybrid_search import hybrid_search
                hits = hybrid_search(q, top_k=top_k, username=username, doc_type=doc_type, use_rerank=True)
            except Exception as e:
                logger.warning("Hybrid search failed, falling back to vector: %s", e)
                from src.rag.vector_store import search as _vector_search
                hits = _vector_search(q, top_k=top_k, username=username, doc_type=doc_type)
        else:
            from src.rag.vector_store import search as _vector_search
            hits = _vector_search(q, top_k=top_k, username=username, doc_type=doc_type)

        # Deduplicate across queries
        for h in hits:
            # Backward compatibility: results may be missing 'id'
            h_id = h.get("id", h.get("_id", f"hit_{len(seen_ids)}"))
            if h_id not in seen_ids:
                seen_ids.add(h_id)
                all_hits.append(h)

    # Sort by score descending
    all_hits.sort(key=lambda x: x.get("score", 0), reverse=True)
    hits = all_hits[:top_k]

    good_hits = [h for h in hits if h["score"] >= RELEVANCE_THRESHOLD]
    need_online = len(good_hits) < MIN_GOOD_HITS

    # Build a single context string from good hits for LLM prompt injection
    if good_hits:
        context_parts = []
        for i, h in enumerate(good_hits, 1):
            source = h["metadata"].get("source", "unknown")
            score = h.get("rrf_score", h.get("score", 0))
            context_parts.append(f"[{i}] (source: {source}, score: {score:.4f})\n{h['text']}")
        context_text = "\n\n---\n\n".join(context_parts)
    else:
        context_text = ""

    return {
        "local_results": good_hits,
        "all_results": hits,
        "need_online": need_online,
        "context_text": context_text,
        "total_hits": len(hits),
        "good_hits": len(good_hits),
        "query_used": queries_to_search[0] if queries_to_search else query,
        "search_mode": search_mode,
    }


def is_rag_available() -> bool:
    """Check if RAG is usable (vector store + embedder both loadable)."""
    try:
        from src.rag.embedder import is_available as embedder_available
        if not embedder_available():
            return False
        from src.rag.vector_store import _get_collection
        return _get_collection() is not None
    except Exception:
        return False


def ingest_text(
    text: str,
    title: str,
    doc_type: str = "research_report",
    username: Optional[str] = None,
    extra_meta: Optional[Dict] = None,
) -> int:
    """Ingest a text block (e.g. a generated report) into the knowledge base.

    This is called after research_skill generates a report to auto-populate
    the RAG store for future queries.

    Returns: number of chunks ingested.
    """
    try:
        from src.rag.vector_store import add_documents, generate_doc_id
        from src.rag.document_loader import chunk_text_block
        import time

        doc_id = generate_doc_id()
        meta = {
            "title": title,
            "type": doc_type,
            "created_at": str(int(time.time())),
        }
        if extra_meta:
            meta.update(extra_meta)

        chunks = chunk_text_block(text, title=title, extra_meta=meta)
        if not chunks:
            return 0
        return add_documents(doc_id, chunks, meta, username=username)
    except Exception as e:
        logger.warning("RAG auto-ingest failed: %s", e)
        return 0
