"""GET/PUT /api/search — Search backend API key management."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.agent.tools import list_search_backends, set_search_api_key, _get_search_api_key

router = APIRouter()


class SearchKeyRequest(BaseModel):
    name: str
    api_key: str


@router.get("/search-backends")
async def get_search_backends():
    return list_search_backends()


@router.put("/search-keys")
async def save_search_key(req: SearchKeyRequest):
    try:
        set_search_api_key(req.name, req.api_key)
        return {"status": "ok", "message": f"{req.name} 搜索 Key 已保存"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))