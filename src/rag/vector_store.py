"""ChromaDB vector store — persistent local file mode.

Stores document chunks as embeddings for semantic search. The store is
partitioned by username (via metadata) so users only retrieve their own
knowledge unless querying the shared collection.
"""
import os
import logging
import uuid
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# 项目根目录（src/rag/vector_store.py → parents[2] = 项目根）
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
# 注意：不要在 import 时读取 os.getenv("CHROMA_PATH")，因为此时 .env 可能
# 尚未加载（server.py 的 load_dotenv 在其后执行）。改为在 _get_collection()
# 内部懒加载，确保读取到最新的环境变量。
_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION", "cs599_knowledge")

_client = None
_collection = None
_resolved_chroma_path: Optional[str] = None  # 缓存已解析的路径，用于日志/stats


def _get_chroma_path() -> str:
    """懒加载 ChromaDB 存储路径。

    优先级：
    1. CHROMA_PATH 环境变量（每次调用都重新读取，确保 .env 加载后生效）
    2. 项目根目录下的 .chroma 目录（与项目绑定，不依赖 cwd）
    """
    env_path = os.getenv("CHROMA_PATH", "").strip()
    if env_path:
        return env_path
    return str(_PROJECT_ROOT / ".chroma")


def _get_collection():
    """Lazy-init ChromaDB client + collection."""
    global _client, _collection, _resolved_chroma_path
    if _collection is not None:
        return _collection
    try:
        import chromadb
        _resolved_chroma_path = _get_chroma_path()
        _client = chromadb.PersistentClient(path=_resolved_chroma_path)
        _collection = _client.get_or_create_collection(
            name=_COLLECTION_NAME,
            metadata={"description": "CS599 RAG knowledge base"},
        )
        logger.info(
            "ChromaDB initialized at %s (collection=%s) — 路径基于项目根目录，"
            "不依赖 cwd，确保知识库持久化一致",
            _resolved_chroma_path, _COLLECTION_NAME,
        )
        return _collection
    except ImportError:
        logger.warning(
            "chromadb not installed; RAG vector store disabled. "
            "Run: pip install chromadb"
        )
        return None
    except Exception as e:
        logger.warning("Failed to init ChromaDB at %s: %s", _get_chroma_path(), e)
        return None


def add_documents(
    doc_id: str,
    chunks: List[Dict[str, str]],
    metadata: Dict,
    username: Optional[str] = None,
) -> int:
    """Add document chunks to the vector store.

    Args:
        doc_id: Unique document identifier.
        chunks: [{"text": "...", "meta": {...}}, ...]
        metadata: Document-level metadata (source, title, type, etc.)
        username: Optional user attribution for per-user filtering.

    Returns:
        Number of chunks added.
    """
    collection = _get_collection()
    if collection is None:
        logger.warning("add_documents 失败：ChromaDB collection 不可用（chromadb 未安装或初始化失败）")
        return 0
    if not chunks:
        logger.warning("add_documents 失败：chunks 为空 (doc_id=%s)", doc_id)
        return 0
    try:
        from src.rag.embedder import embed
        texts = [c["text"] for c in chunks]
        embeddings = embed(texts)
        if not embeddings:
            logger.warning("add_documents 失败：embedder 返回空（doc_id=%s, chunks=%d）", doc_id, len(chunks))
            return 0
        ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
        metadatas = []
        for i, c in enumerate(chunks):
            m = {**metadata, **c.get("meta", {}), "chunk_idx": i, "doc_id": doc_id}
            if username is not None:
                m["username"] = username
            metadatas.append(m)
        # ChromaDB 有内置的 max_batch_size（默认 5461），分批写入避免超出限制
        batch_size = 1000
        total = len(ids)
        for start in range(0, total, batch_size):
            end = min(start + batch_size, total)
            collection.upsert(
                ids=ids[start:end],
                embeddings=embeddings[start:end],
                documents=texts[start:end],
                metadatas=metadatas[start:end],
            )
        logger.info("Added %d chunks for doc %s at %s (batched)", total, doc_id, _resolved_chroma_path)
        return len(chunks)
    except Exception as e:
        logger.warning("Failed to add documents (doc_id=%s): %s", doc_id, e)
        return 0


def search(
    query: str,
    top_k: int = 5,
    username: Optional[str] = None,
    doc_type: Optional[str] = None,
) -> List[Dict]:
    """Search for similar chunks.

    Args:
        query: Search query text.
        top_k: Number of results.
        username: If set, filter to only this user's documents.
        doc_type: If set, filter by document type (e.g. "research_report").

    Returns:
        [{"id", "text", "score", "metadata"}] sorted by score descending.
    """
    collection = _get_collection()
    if collection is None:
        return []
    try:
        from src.rag.embedder import embed_one
        q_emb = embed_one(query)
        where_filter = {}
        if username is not None:
            where_filter["username"] = username
        if doc_type is not None:
            where_filter["type"] = doc_type
        results = collection.query(
            query_embeddings=[q_emb],
            n_results=top_k,
            where=where_filter if where_filter else None,
        )
        hits = []
        if results and results.get("documents"):
            docs = results["documents"][0]
            metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
            dists = results["distances"][0] if results.get("distances") else [0] * len(docs)
            ids = results["ids"][0] if results.get("ids") else ["" ] * len(docs)
            for _id, doc, meta, dist in zip(ids, docs, metas, dists):
                # ChromaDB returns distance; lower = more similar.
                # Convert to similarity score (1 - distance for cosine).
                score = max(0, 1 - dist)
                hits.append({
                    "id": _id,
                    "text": doc,
                    "score": round(score, 4),
                    "metadata": meta,
                })
        return hits
    except Exception as e:
        logger.warning("Vector search failed: %s", e)
        return []


def delete_document(doc_id: str) -> int:
    """Delete all chunks belonging to a document. Returns count deleted."""
    collection = _get_collection()
    if collection is None:
        return 0
    try:
        # ChromaDB supports deletion by metadata filter
        results = collection.get(where={"doc_id": doc_id})
        ids = results.get("ids", []) if results else []
        if ids:
            collection.delete(ids=ids)
            logger.info("Deleted %d chunks for doc %s", len(ids), doc_id)
        return len(ids)
    except Exception as e:
        logger.warning("Failed to delete doc %s: %s", doc_id, e)
        return 0


def list_documents(username: Optional[str] = None) -> List[Dict]:
    """List all documents in the store (deduplicated by doc_id)."""
    collection = _get_collection()
    if collection is None:
        return []
    try:
        where_filter = {}
        if username is not None:
            where_filter["username"] = username
        results = collection.get(
            where=where_filter if where_filter else None,
            include=["metadatas"],
        )
        if not results or not results.get("metadatas"):
            return []
        # Deduplicate by doc_id, keeping the first chunk's metadata
        seen = {}
        for meta in results["metadatas"]:
            did = meta.get("doc_id", "unknown")
            if did not in seen:
                seen[did] = {
                    "doc_id": did,
                    "title": meta.get("title", did),
                    "source": meta.get("source", ""),
                    "type": meta.get("type", "unknown"),
                    "username": meta.get("username", ""),
                    "created_at": meta.get("created_at", ""),
                }
        return list(seen.values())
    except Exception as e:
        logger.warning("Failed to list documents: %s", e)
        return []


def get_stats() -> Dict:
    """Return store statistics."""
    collection = _get_collection()
    if collection is None:
        return {"enabled": False, "total_chunks": 0, "total_documents": 0, "path": _get_chroma_path()}
    try:
        count = collection.count()
        docs = list_documents()
        return {
            "enabled": True,
            "total_chunks": count,
            "total_documents": len(docs),
            "collection": _COLLECTION_NAME,
            "path": _resolved_chroma_path or _get_chroma_path(),
        }
    except Exception as e:
        return {"enabled": False, "error": str(e), "path": _resolved_chroma_path or _get_chroma_path()}


def get_all_documents() -> List[Dict]:
    """Get ALL document chunks with their metadata (for BM25 index building).

    Returns:
        [{"id": str, "text": str, "metadata": dict}, ...]
        Empty list if store is unavailable.
    """
    collection = _get_collection()
    if collection is None:
        return []
    try:
        results = collection.get(include=["documents", "metadatas"])
        if not results or not results.get("ids"):
            return []
        docs = []
        ids = results["ids"]
        documents = results.get("documents", [None] * len(ids))
        metadatas = results.get("metadatas", [{}] * len(ids))
        for _id, doc, meta in zip(ids, documents, metadatas):
            if doc is not None:
                docs.append({"id": _id, "text": doc, "metadata": meta or {}})
        logger.debug("get_all_documents returned %d chunks", len(docs))
        return docs
    except Exception as e:
        logger.warning("get_all_documents failed: %s", e)
        return []


def generate_doc_id() -> str:
    """Generate a unique document ID."""
    return f"doc_{uuid.uuid4().hex[:12]}"
