"""API routes for search history."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from src.storage.database import get_db, get_recent_searches, SearchHistory

router = APIRouter(tags=["search_history"])


@router.get("/api/search-history")
def list_search_history(
    limit: int = Query(default=20, ge=1, le=100),
    username: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    """List recent search history."""
    records = get_recent_searches(db, limit=limit, username=username)
    return {
        "total": len(records),
        "items": [
            {
                "id": r.id,
                "topic": r.topic,
                "num_sources": r.num_sources,
                "num_papers_cited": r.num_papers_cited,
                "report_preview": r.report_preview,
                "duration_seconds": r.duration_seconds,
                "provider": r.provider,
                "model": r.model,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in records
        ],
    }


@router.get("/api/search-history/stats")
def search_stats(
    username: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    """Get search statistics."""
    from sqlalchemy import func
    query = db.query(
        func.count(SearchHistory.id).label("total_searches"),
        func.avg(SearchHistory.duration_seconds).label("avg_duration"),
        func.avg(SearchHistory.num_papers_cited).label("avg_papers_cited"),
        func.sum(SearchHistory.num_papers_cited).label("total_papers_cited"),
    )
    if username is not None:
        query = query.filter(SearchHistory.username == username)
    row = query.first()
    # 当表为空时，SQL 聚合函数 COUNT 返回 0，但 SUM/AVG 返回 NULL。
    # 必须对所有字段做 NULL → 0 兜底，否则前端显示 "null" 或报错。
    total_searches = (row.total_searches if row else 0) or 0
    avg_duration = (row.avg_duration if row else None) or 0
    avg_papers = (row.avg_papers_cited if row else None) or 0
    total_papers = (row.total_papers_cited if row else None) or 0
    return {
        "total_searches": total_searches,
        "avg_duration_seconds": round(avg_duration, 2),
        "avg_papers_cited": round(avg_papers, 2),
        "total_papers_cited": total_papers,
    }
