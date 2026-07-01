"""Hybrid search — BM25 + vector + rerank fusion.

Combines keyword (BM25) and semantic (embedding) search results using
Reciprocal Rank Fusion (RRF), then applies a cross-encoder reranker for
final re-scoring.
"""
import os
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

RRF_K = int(os.getenv("RAG_RRF_K", "60"))  # RRF constant (k in 1/(k+rank))
RERANK_TOP_K = int(os.getenv("RAG_RERANK_TOP_K", "20"))  # candidates before rerank


# ── BM25 Index (lazy-built from ChromaDB texts) ──────────────────────────

_BM25_INDEX = None      # rank_bm25 BM25Okapi instance
_BM25_TEXTS = None      # original texts for each indexed position
_BM25_IDS = None        # original ids for each indexed position
_BM25_METADATAS = None  # original metadatas for each position


def _build_bm25_index():
    """Build or rebuild the BM25 index from ChromaDB's stored documents."""
    global _BM25_INDEX, _BM25_TEXTS, _BM25_IDS, _BM25_METADATAS
    try:
        from src.rag.vector_store import get_all_documents
        from rank_bm25 import BM25Okapi
        import tokenizers

        all_docs = get_all_documents()
        if not all_docs:
            logger.warning("BM25 index: no documents found in ChromaDB")
            _BM25_INDEX = None
            return

        _BM25_TEXTS = [d["text"] for d in all_docs]
        _BM25_IDS = [d["id"] for d in all_docs]
        _BM25_METADATAS = [d.get("metadata", {}) for d in all_docs]

        # Tokenize using whitespace + lower
        tokenized = [text.lower().split() for text in _BM25_TEXTS]
        _BM25_INDEX = BM25Okapi(tokenized)
        logger.info("BM25 index built with %d documents", len(_BM25_TEXTS))
    except ImportError as e:
        logger.warning("BM25 not available: %s. Run: pip install rank_bm25 tokenizers", e)
        _BM25_INDEX = None
    except Exception as e:
        logger.warning("Failed to build BM25 index: %s", e)
        _BM25_INDEX = None


def bm25_search(query: str, top_k: int = 5) -> List[Dict]:
    """Search using BM25 keyword matching."""
    global _BM25_INDEX, _BM25_TEXTS, _BM25_IDS, _BM25_METADATAS

    if _BM25_INDEX is None:
        _build_bm25_index()
    if _BM25_INDEX is None:
        return []

    try:
        tokenized = query.lower().split()
        scores = _BM25_INDEX.get_scores(tokenized)
        scored = list(enumerate(scores))
        scored.sort(key=lambda x: x[1], reverse=True)
        top = scored[:top_k]

        results = []
        for idx, score in top:
            if score <= 0:
                continue
            results.append({
                "id": _BM25_IDS[idx],
                "text": _BM25_TEXTS[idx],
                "score": round(float(score), 4),
                "metadata": _BM25_METADATAS[idx],
                "source": "bm25",
            })
        return results
    except Exception as e:
        logger.warning("BM25 search failed: %s", e)
        return []


# ── RRF Fusion ──────────────────────────────────────────────────────────

def _rrf_merge(vector_results: List[Dict], bm25_results: List[Dict],
                top_k: int, k: int = RRF_K) -> List[Dict]:
    """Merge two ranked lists using Reciprocal Rank Fusion."""
    scores: Dict[str, float] = {}

    for rank, r in enumerate(vector_results):
        doc_id = r["id"]
        scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank + 1)

    for rank, r in enumerate(bm25_results):
        doc_id = r["id"]
        scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank + 1)

    # Sort by fused score descending
    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

    merged = {}
    for r in vector_results:
        merged[r["id"]] = r
    for r in bm25_results:
        if r["id"] not in merged:
            merged[r["id"]] = r

    result = []
    for doc_id in sorted_ids[:top_k]:
        item = dict(merged[doc_id])
        item["rrf_score"] = round(scores[doc_id], 4)
        item["source"] = "hybrid"
        result.append(item)

    return result


# ── Reranker (cross-encoder) ────────────────────────────────────────────

_RERANKER = None


def _get_reranker():
    """Lazy-load the FlashRank cross-encoder reranker."""
    global _RERANKER
    if _RERANKER is not None:
        return _RERANKER
    try:
        from flashrank import Ranker
        # Use a lightweight cross-encoder model
        _RERANKER = Ranker(model_name="ms-marco-MiniLM-L-12-v2", cache_dir=os.getenv("FLASHRANK_CACHE") or None)
        logger.info("FlashRank reranker loaded (ms-marco-MiniLM-L-12-v2)")
        return _RERANKER
    except ImportError:
        logger.warning("flashrank not installed; reranking disabled. Run: pip install flashrank")
        return None
    except Exception as e:
        logger.warning("Failed to load reranker: %s", e)
        return None


def rerank(query: str, results: List[Dict], top_k: int = 5) -> List[Dict]:
    """Re-rank results using a cross-encoder.

    Args:
        query: Original search query.
        results: List of {"id", "text", ...} to re-rank.
        top_k: Number of results to return after re-ranking.

    Returns:
        Re-ranked results list (top_k items).
    """
    ranker = _get_reranker()
    if ranker is None:
        # Fallback: sort by existing score
        return sorted(results, key=lambda x: x.get("score", 0), reverse=True)[:top_k]

    try:
        passages = []
        for r in results:
            passages.append({
                "id": r["id"],
                "text": r["text"][:512],  # truncate for speed
                "meta": r.get("metadata", {}),
            })

        reranked = ranker.rerank(query, passages)
        final = []
        for item in reranked[:top_k]:
            final.append({
                "id": item["id"],
                "text": item["text"],
                "score": round(float(item["score"]), 4),
                "metadata": item.get("meta", {}),
                "source": "reranked",
            })
        return final
    except Exception as e:
        logger.warning("Reranking failed: %s", e)
        return sorted(results, key=lambda x: x.get("score", 0), reverse=True)[:top_k]


# ── Public API ──────────────────────────────────────────────────────────

def hybrid_search(
    query: str,
    top_k: int = 5,
    username: Optional[str] = None,
    doc_type: Optional[str] = None,
    use_rerank: bool = True,
) -> List[Dict]:
    """Hybrid search: vector + BM25 + optional rerank.

    Args:
        query: Search query.
        top_k: Final number of results.
        username: Filter by username (passed to vector search).
        doc_type: Filter by document type.
        use_rerank: Whether to apply cross-encoder reranking.

    Returns:
        [{"id", "text", "score", "metadata", "source"}] sorted by relevance.
    """
    # 1. Vector search
    from src.rag.vector_store import search as vector_search
    vector_results = vector_search(query, top_k=RERANK_TOP_K, username=username, doc_type=doc_type)

    # 2. BM25 search
    bm25_results = bm25_search(query, top_k=RERANK_TOP_K)

    # 3. RRF fusion
    if not bm25_results:
        fused = vector_results[:RERANK_TOP_K]
    elif not vector_results:
        fused = bm25_results[:RERANK_TOP_K]
    else:
        fused = _rrf_merge(vector_results, bm25_results, top_k=RERANK_TOP_K)

    if not fused:
        return []

    # 4. Rerank
    if use_rerank and len(fused) > 1:
        return rerank(query, fused, top_k=top_k)
    else:
        return sorted(fused, key=lambda x: x.get("rrf_score", x.get("score", 0)),
                      reverse=True)[:top_k]