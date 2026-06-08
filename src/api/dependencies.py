"""Shared API dependencies — provider/model resolution and API key checks.

Extracted from generation.py, agents.py, and assistant.py to eliminate
code duplication (DRY).
"""
from typing import Tuple, Optional

from src.models.manager import get_model_manager
from src.models.key_store import get_key_store


def resolve_provider_model(req_provider: str = "", req_model: str = "") -> Tuple[str, str]:
    """Get provider & model — prefer request params, then configured default.

    Returns:
        (provider_name, model_id)
    """
    mgr = get_model_manager()
    if req_provider:
        p = mgr.get_provider(req_provider)
        if p:
            return p.config.name, req_model or p.config.default_model or "deepseek-chat"
    default = mgr.default_provider
    if default:
        cfg = next((c for c in mgr.list_providers() if c.name == default), None)
        if cfg:
            return cfg.name, cfg.default_model or "deepseek-chat"
    providers = mgr.list_providers()
    if providers:
        p = providers[0]
        return p.name, p.default_model or "deepseek-chat"
    return "deepseek", "deepseek-chat"


def has_api_key(provider_name: str) -> bool:
    """Check if provider has a valid API key configured."""
    ks = get_key_store()
    key = ks.get_key(provider_name)
    return bool(key and key.strip() and key.strip() != "no-key" and key.strip() != "YOUR_API_KEY")


def get_llm_client(provider: str, model: str, temperature: float = 0.7):
    """Create an LLM client for the given provider/model."""
    mgr = get_model_manager()
    return mgr.create_llm_client(provider, model, temperature)