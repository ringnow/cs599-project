"""Model Manager - central hub for managing multiple model providers.

Inspired by CC Switch's design:
- Select a preset -> Enter API Key -> Provider ready
- Health check with status display
- One-click provider activation
"""
import json
from typing import Dict, List, Optional
from pathlib import Path

from src.models.provider import (
    ProviderConfig, ModelInfo, ModelProvider,
    BUILTIN_PRESETS, BUILTIN_PROVIDERS, ProviderPreset, ProviderType,
    get_preset, get_preset_list,
)
from src.models.key_store import get_key_store

CONFIG_DIR = Path.home() / ".cs599-agent"
PROVIDERS_FILE = CONFIG_DIR / "providers.json"


class ModelManager:
    """Central manager for all model providers."""

    def __init__(self):
        self._providers: Dict[str, ModelProvider] = {}
        self._configs: Dict[str, ProviderConfig] = {}
        self._key_store = get_key_store()
        self._load_providers()

    # --- Loading ---

    def _load_providers(self):
        """Load from storage or use defaults."""
        if PROVIDERS_FILE.exists():
            try:
                data = json.loads(PROVIDERS_FILE.read_text())
                for name, config_data in data.items():
                    cfg = ProviderConfig.from_dict(config_data)
                    self._configs[name] = cfg
            except Exception:
                self._use_defaults()
        else:
            self._use_defaults()
        self._refresh_providers()

    def _use_defaults(self):
        """Use built-in provider presets."""
        from dataclasses import replace
        self._configs = {name: replace(cfg) for name, cfg in BUILTIN_PROVIDERS.items()}

    def _save_configs(self):
        """Save to storage."""
        data = {name: cfg.to_dict() for name, cfg in self._configs.items()}
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        PROVIDERS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def _refresh_providers(self):
        """Refresh ModelProvider instances."""
        self._providers = {}
        for name, config in self._configs.items():
            if not config.is_active:
                continue
            api_key = self._key_store.get_key(name) or config.api_key
            mp = ModelProvider(config, api_key)
            self._providers[name] = mp

    # --- Provider CRUD ---

    def list_providers(self) -> List[ProviderConfig]:
        """List all configured providers."""
        return list(self._configs.values())

    @property
    def default_provider(self) -> Optional[str]:
        """Return the first active provider that has an API key configured."""
        for name, cfg in self._configs.items():
            if cfg.is_active and (self._key_store.has_key(name) or cfg.api_key):
                return name
        for name in self._configs:
            return name
        return None

    def get_active_providers(self) -> List[ProviderConfig]:
        """List active providers."""
        return [p for p in self._configs.values() if p.is_active]

    def get_provider(self, name: str) -> Optional[ModelProvider]:
        """Get a ModelProvider instance."""
        self._refresh_providers()  # Refresh in case key was just set
        return self._providers.get(name)

    # --- Preset-based creation (CC Switch style) ---

    def get_presets(self) -> List[ProviderPreset]:
        """Get all available preset templates."""
        return get_preset_list()

    def add_provider_from_preset(self, preset_name: str, api_key: str = "",
                                  custom_name: str = "",
                                  custom_base_url: str = "") -> tuple[bool, str]:
        """Create a provider from a preset template.

        CC Switch style: Select preset -> Enter API Key -> Done.

        Returns: (success, message)
        """
        preset = get_preset(preset_name)
        if not preset:
            return False, f"预设 '{preset_name}' 不存在"

        name = custom_name or preset.name
        base_url = custom_base_url or preset.base_url

        # Check if already exists
        if name in self._configs and name in BUILTIN_PROVIDERS:
            # Just update the key
            self.set_api_key(name, api_key)
            return True, f"已更新 '{name}' 的 API Key"

        config = ProviderConfig(
            name=name,
            display_name=preset.display_name,
            type=preset.type,
            base_url=base_url,
            api_key_env=preset.api_key_env,
            api_key=api_key,
            default_model=preset.default_model,
        )

        self._configs[name] = config
        self.set_api_key(name, api_key)
        self._save_configs()
        self._refresh_providers()
        return True, f"已添加 Provider '{name}' ({preset.display_name})"

    def add_custom_provider(self, name: str, display_name: str,
                            base_url: str, api_key: str,
                            default_model: str = "") -> tuple[bool, str]:
        """Add a fully custom provider."""
        if not name or not base_url:
            return False, "名称和 Base URL 不能为空"
        if not base_url.startswith("http"):
            return False, "Base URL 必须以 http:// 或 https:// 开头"

        config = ProviderConfig(
            name=name,
            display_name=display_name or name,
            type=ProviderType.OPENAI_COMPATIBLE,
            base_url=base_url,
            api_key=api_key,
            default_model=default_model or "default",
        )
        self._configs[name] = config
        if api_key:
            self.set_api_key(name, api_key)
        self._save_configs()
        self._refresh_providers()
        return True, f"已添加自定义 Provider '{name}'"

    def remove_provider(self, name: str) -> bool:
        """Remove a provider (can't remove built-in)."""
        if name in BUILTIN_PROVIDERS and name != "custom":
            return False
        if name in self._configs:
            del self._configs[name]
            self._key_store.remove_key(name)
            self._save_configs()
            self._refresh_providers()
            return True
        return False

    def update_provider(self, name: str, **kwargs) -> bool:
        """Update provider config."""
        if name not in self._configs:
            return False
        cfg = self._configs[name]
        for key, value in kwargs.items():
            if hasattr(cfg, key):
                setattr(cfg, key, value)
        self._save_configs()
        self._refresh_providers()
        return True

    # --- Model Discovery ---

    def discover_models(self, provider_name: str) -> List[ModelInfo]:
        """Discover models from a specific provider."""
        provider = self._providers.get(provider_name)
        if not provider:
            return []
        models = provider.discover_models()
        if models:
            self._configs[provider_name].models = models
            self._save_configs()
        return models

    def get_all_models(self, provider_name: Optional[str] = None) -> List[ModelInfo]:
        """Get models - from cache or discovery."""
        if provider_name:
            cfg = self._configs.get(provider_name)
            if cfg and cfg.models:
                return cfg.models
            return self.discover_models(provider_name)

        all_models = []
        for name in self._providers:
            models = self.get_all_models(name)
            for m in models:
                m.provider = name
            all_models.extend(models)
        return all_models

    # --- API Key ---

    def set_api_key(self, provider_name: str, api_key: str):
        """Set API key for a provider."""
        self._key_store.set_key(provider_name, api_key)
        if provider_name in self._configs:
            self._configs[provider_name].api_key = api_key
            self._save_configs()
        # Reset client so it picks up new key
        if provider_name in self._providers:
            self._providers[provider_name].api_key = api_key
            self._providers[provider_name].reset_client()

    def get_api_key(self, provider_name: str) -> Optional[str]:
        return self._key_store.get_key(provider_name)

    def has_api_key(self, provider_name: str) -> bool:
        return self._key_store.has_key(provider_name)

    def remove_api_key(self, provider_name: str):
        self._key_store.remove_key(provider_name)
        if provider_name in self._configs:
            self._configs[provider_name].api_key = ""
            self._save_configs()
        if provider_name in self._providers:
            self._providers[provider_name].reset_client()

    # --- LLM Client ---

    def create_llm_client(self, provider_name: str, model_id: str, temperature: float = 0.7):
        from langchain_openai import ChatOpenAI
        provider = self._providers.get(provider_name)
        if not provider:
            raise ValueError(f"Provider '{provider_name}' 不存在或未激活")
        if not provider.config.base_url:
            raise ValueError(f"Provider '{provider_name}' 的 base_url 未配置")
        return ChatOpenAI(
            model=model_id,
            api_key=provider.api_key or "no-key",
            base_url=provider.config.base_url,
            temperature=temperature,
            timeout=120,  # 单次 LLM 调用等待上限（用户 API 较慢）
            max_retries=0,  # 不重试，失败则快速返回
        )

    # --- Health Check ---

    def health_check(self, provider_name: Optional[str] = None) -> Dict[str, dict]:
        """Check health. Returns {name: {healthy, message}}."""
        if provider_name:
            provider = self._providers.get(provider_name)
            if provider:
                h, m = provider.health_check()
                return {provider_name: {"healthy": h, "message": m}}
            return {provider_name: {"healthy": False, "message": "Provider 不存在"}}
        return {
            name: {"healthy": h, "message": m}
            for name, p in self._providers.items()
            for h, m in [p.health_check()]
        }

    # --- Status Summary ---

    def get_status_summary(self) -> List[dict]:
        """Get full status for UI display."""
        health = self.health_check()
        result = []
        for cfg in self._configs.values():
            h = health.get(cfg.name, {"healthy": False, "message": "未激活"})
            result.append({
                "name": cfg.name,
                "display_name": cfg.display_name,
                "base_url": cfg.base_url,
                "default_model": cfg.default_model,
                "has_key": self.has_api_key(cfg.name),
                "is_active": cfg.is_active,
                "healthy": h["healthy"],
                "health_message": h["message"],
                "type": cfg.type.value,
            })
        return result


_manager = None


def get_model_manager() -> ModelManager:
    global _manager
    if _manager is None:
        _manager = ModelManager()
    return _manager
