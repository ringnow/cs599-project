"""Knowledge base management API routes.

Endpoints:
  POST   /api/knowledge/upload       — Upload PDF/TXT/MD → parse → chunk → embed
  GET    /api/knowledge/documents    — List all documents
  DELETE /api/knowledge/documents/{doc_id} — Delete a document
  GET    /api/knowledge/search       — Semantic search (debugging/preview)
  GET    /api/knowledge/stats        — Store statistics
  POST   /api/knowledge/ingest-text  — Ingest raw text (e.g. from research reports)
"""
import os
import tempfile
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(tags=["knowledge"])

# Allowed upload extensions + max file size (10 MB)
ALLOWED_EXTS = {".pdf", ".txt", ".md"}
MAX_FILE_SIZE = 10 * 1024 * 1024


class IngestTextRequest(BaseModel):
    """Ingest a raw text block into the knowledge base."""
    text: str = Field(..., min_length=10, max_length=50000)
    title: str = Field(..., min_length=1, max_length=200)
    doc_type: str = Field(default="research_report")


class SearchResponse(BaseModel):
    query: str
    total: int
    results: list


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    provider_name: Optional[str] = None
    model_id: Optional[str] = None


class AskResponse(BaseModel):
    answer: str
    sources: list
    total_sources: int


@router.get("/api/knowledge/stats")
def knowledge_stats():
    """Get knowledge base statistics."""
    from src.rag.vector_store import get_stats
    from src.rag.embedder import is_available
    stats = get_stats()
    stats["embedder_available"] = is_available()
    return stats


@router.get("/api/knowledge/documents")
def list_documents(
    username: Optional[str] = Query(default=None),
    request: Request = None,
):
    """List all documents in the knowledge base."""
    from src.rag.vector_store import list_documents as _list
    # If no explicit username query param, use the authenticated user
    effective_user = username
    if effective_user is None and request is not None:
        effective_user = getattr(request.state, "user", None)
    return {"documents": _list(username=effective_user)}


@router.post("/api/knowledge/upload")
async def upload_document(
    file: UploadFile = File(...),
    request: Request = None,
):
    """Upload a PDF/TXT/MD file → parse → chunk → embed → store."""
    # Validate extension
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Allowed: {', '.join(sorted(ALLOWED_EXTS))}",
        )

    # Read and validate size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large: {len(content)} bytes (max {MAX_FILE_SIZE})",
        )

    # Save to temp file for parsing
    username = getattr(request.state, "user", None) if request else None
    try:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False, mode="wb") as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        from src.rag.document_loader import load_and_chunk
        from src.rag.vector_store import add_documents, generate_doc_id

        doc_id = generate_doc_id()
        import time
        meta = {
            "title": file.filename,
            "type": "uploaded_file",
            "source": file.filename,
            "created_at": str(int(time.time())),
        }
        chunks = load_and_chunk(tmp_path, extra_meta=meta)
        if not chunks:
            raise HTTPException(status_code=422, detail="No text could be extracted from the file")

        added = add_documents(doc_id, chunks, meta, username=username)
        if added == 0:
            # 上传成功但入库失败 —— 通常是 embedder 不可用或 ChromaDB 故障
            raise HTTPException(
                status_code=500,
                detail="文档已解析但入库失败（chunks=0）。请检查 RAG embedder 是否可用（EMBEDDING_MODEL 配置）以及 ChromaDB 是否正常初始化。查看后端日志获取详情。",
            )
        return {
            "doc_id": doc_id,
            "filename": file.filename,
            "chunks_added": added,
            "message": f"Successfully ingested {added} chunks",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Upload failed")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
    finally:
        if "tmp_path" in locals():
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


@router.delete("/api/knowledge/documents/{doc_id}")
def delete_document(doc_id: str):
    """Delete a document and all its chunks."""
    from src.rag.vector_store import delete_document as _delete
    deleted = _delete(doc_id)
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"doc_id": doc_id, "chunks_deleted": deleted}


@router.get("/api/knowledge/search", response_model=SearchResponse)
def search_knowledge(
    q: str = Query(..., min_length=1, max_length=500),
    top_k: int = Query(default=5, ge=1, le=20),
    username: Optional[str] = Query(default=None),
    doc_type: Optional[str] = Query(default=None),
    request: Request = None,
):
    """Hybrid search the knowledge base (BM25 + vector + rerank)."""
    from src.rag.hybrid_search import hybrid_search as _hs
    from src.rag.embedder import is_available as rag_available
    effective_user = username
    if effective_user is None and request is not None:
        effective_user = getattr(request.state, "user", None)
    if not rag_available():
        return SearchResponse(query=q, total=0, results=[])
    results = _hs(q, top_k=top_k, username=effective_user, doc_type=doc_type)
    return SearchResponse(query=q, total=len(results), results=results)


@router.post("/api/knowledge/ingest-text")
def ingest_text_endpoint(req: IngestTextRequest, request: Request):
    """Ingest a raw text block (e.g. a generated research report) into the
    knowledge base. Used for auto-ingestion after report generation, or
    manual text ingestion from the UI.
    """
    from src.rag.retriever import ingest_text
    username = getattr(request.state, "user", None) if request else None
    chunks = ingest_text(
        text=req.text,
        title=req.title,
        doc_type=req.doc_type,
        username=username,
    )
    if chunks == 0:
        raise HTTPException(status_code=500, detail="Ingestion failed — RAG may not be available")
    return {"chunks_ingested": chunks, "title": req.title, "message": "Text ingested successfully"}


@router.post("/api/knowledge/ask", response_model=AskResponse)
def knowledge_ask(req: AskRequest, request: Request):
    """RAG Q&A: hybrid search → rerank → LLM answer grounded in sources."""
    from src.rag.retriever import retrieve
    from src.rag.embedder import is_available as rag_available

    if not rag_available():
        raise HTTPException(status_code=503, detail="RAG is not available (embedder not loaded)")

    # 1. Retrieve via hybrid pipeline (query optimization + BM25 + vector + rerank)
    effective_user = getattr(request.state, "user", None) if request else None
    rag_result = retrieve(req.question, top_k=req.top_k, username=effective_user)

    # Use ALL results (not just high-scoring ones) for context building
    all_results = rag_result.get("all_results", rag_result["local_results"])
    if not all_results:
        return AskResponse(answer="知识库中未找到与问题相关的信息。请先上传文档或运行研究任务。", sources=[], total_sources=0)

    # 2. Build context from ALL retrieved chunks
    context_parts = []
    sources = []
    for r in all_results:
        text = r.get("text", "")
        meta = r.get("metadata", {})
        source_name = meta.get("source") or meta.get("title", "unknown")
        context_parts.append(f"[来源: {source_name}]\n{text}")
        sources.append({"text": text[:200], "source": source_name, "score": r.get("score", 0)})

    context_text = "\n\n---\n\n".join(context_parts)

    # 3. Build LLM prompt
    prompt = f"""你是一个知识库问答助手。请根据以下知识库内容，回答用户的问题。

## 知识库内容\n{context_text}\n
## 用户问题\n{req.question}\n
## 要求
- 请基于知识库内容回答，如果知识库内容不足以回答问题，请明确说明
- 回答时引用具体来源
- 使用专业、清晰的中文回答
"""

    # 4. Call LLM
    from src.api.dependencies import resolve_provider_model
    from src.models.manager import get_model_manager

    provider_name = req.provider_name
    model_id = req.model_id
    if not provider_name or not model_id:
        resolved_provider, resolved_model = resolve_provider_model()
        provider_name = provider_name or resolved_provider
        model_id = model_id or resolved_model

    mgr = get_model_manager()
    try:
        llm = mgr.create_llm_client(provider_name, model_id, 0.3)
        msg = [{"role": "user", "content": prompt}]
        resp = llm.invoke(msg)
        answer = resp.content if hasattr(resp, "content") else str(resp)
    except Exception as e:
        logger.warning("LLM call in RAG QA failed: %s", e)
        # Fallback: return raw search results as plain text
        fallback_lines = [f"[{r.get('score', 0):.2f}] {r.get('text', '')[:300]}"
                          for r in all_results[:3]]
        answer = "（LLM 回答失败，以下为知识库检索结果）\n\n" + "\n\n".join(fallback_lines)

    return AskResponse(answer=answer, sources=sources, total_sources=len(sources))
