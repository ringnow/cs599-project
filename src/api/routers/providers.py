"""CRUD /api/providers — LLM provider management."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from src.models.manager import get_model_manager

router = APIRouter()


class ProviderResponse(BaseModel):
    name: str
    display_name: str
    base_url: str
    default_model: str
    has_key: bool
    is_active: bool


class AddProviderRequest(BaseModel):
    preset_name: str
    api_key: str = ""
    custom_base_url: Optional[str] = None


class AddCustomProviderRequest(BaseModel):
    name: str
    display_name: str = ""
    base_url: str
    api_key: str = ""
    default_model: str = ""


class UpdateProviderRequest(BaseModel):
    base_url: Optional[str] = None
    default_model: Optional[str] = None


class SetKeyRequest(BaseModel):
    api_key: str


@router.get("/providers", response_model=List[ProviderResponse])
async def list_providers():
    mgr = get_model_manager()
    providers = mgr.list_providers()
    return [
        ProviderResponse(
            name=p.name,
            display_name=p.display_name,
            base_url=p.base_url,
            default_model=p.default_model or "",
            has_key=mgr.has_api_key(p.name),
            is_active=True,
        )
        for p in providers
    ]


@router.get("/providers/presets")
async def list_presets():
    from src.models.provider import get_preset_list
    presets = get_preset_list()
    return {"presets": [{"name": p.name, "display_name": p.display_name,
                         "base_url": p.base_url, "default_model": p.default_model,
                         "description": p.description, "website": p.website}
                        for p in presets]}


@router.post("/providers")
async def add_provider(req: AddProviderRequest):
    mgr = get_model_manager()
    try:
        mgr.add_provider_from_preset(req.preset_name, req.api_key, req.custom_base_url)
        return {"status": "ok", "message": f"服务商 {req.preset_name} 已添加"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/providers/custom")
async def add_custom_provider(req: AddCustomProviderRequest):
    mgr = get_model_manager()
    try:
        success, msg = mgr.add_custom_provider(
            name=req.name,
            display_name=req.display_name or req.name,
            base_url=req.base_url,
            api_key=req.api_key,
            default_model=req.default_model,
        )
        if not success:
            raise HTTPException(status_code=400, detail=msg)
        return {"status": "ok", "message": msg}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/providers/{name}")
async def update_provider(name: str, req: UpdateProviderRequest):
    mgr = get_model_manager()
    try:
        mgr.update_provider(name, base_url=req.base_url, default_model=req.default_model)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/providers/{name}")
async def delete_provider(name: str):
    mgr = get_model_manager()
    try:
        mgr.remove_provider(name)
        return {"status": "ok", "message": f"服务商 {name} 已删除"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/providers/{name}/key")
async def set_provider_key(name: str, req: SetKeyRequest):
    mgr = get_model_manager()
    try:
        mgr.set_api_key(name, req.api_key)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/providers/{name}/models")
async def discover_models(name: str):
    mgr = get_model_manager()
    try:
        models = mgr.discover_models(name)
        return {"models": models}
    except Exception as e:
        return {"models": []}


@router.get("/providers/health")
async def providers_health():
    mgr = get_model_manager()
    results = {}
    for p in mgr.list_providers():
        try:
            test_llm = mgr.create_llm_client(p.name, p.default_model or "deepseek-chat", 0.1)
            resp = test_llm.invoke([{"role": "user", "content": "ping"}])
            results[p.name] = {"healthy": True}
        except Exception:
            results[p.name] = {"healthy": False}
    return results