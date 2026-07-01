"""API route for cache statistics."""
from fastapi import APIRouter
from src.storage.cache import cache_stats

router = APIRouter(tags=["cache"])


@router.get("/api/cache/stats")
def get_cache_stats():
    """Get Redis cache statistics."""
    return cache_stats()
