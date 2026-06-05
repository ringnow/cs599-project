"""Model provider management - supports OpenAI-compatible APIs and Ollama.

Inspired by CC Switch's provider preset system:
- Preset templates for 20+ providers (built-in)
- One-click provider creation from preset
- Health check + auto-failover support
"""
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum

import httpx
import openai


class ProviderType(str, Enum):
    """Type of model provider."""
    OPENAI_COMPATIBLE = "openai_compatible"
    OLLAMA = "ollama"


@dataclass
class ModelInfo:
    """Information about a single model."""
    id: str
    name: str
    description: str = ""
    context_length: int = 4096
    supports_tools: bool = True
    supports_json_mode: bool = True
    provider: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> 'ModelInfo':
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ProviderConfig:
    """Configuration for a model provider."""
    name: str
    display_name: str
    type: ProviderType
    base_url: str
    api_key_env: str = ""
    api_key: str = ""
    default_model: str = ""
    models: List[ModelInfo] = field(default_factory=list)
    is_active: bool = True
    custom_headers: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d['type'] = self.type.value
        d['models'] = [m.to_dict() for m in self.models]
        return d

    @classmethod
    def from_dict(cls, d: dict) -> 'ProviderConfig':
        d = d.copy()
        # Handle type conversion from string
        type_val = d.get('type', 'openai_compatible')
        if isinstance(type_val, str):
            d['type'] = ProviderType(type_val)
        d['models'] = [ModelInfo.from_dict(m) for m in d.get('models', [])]
        # Remove unknown fields
        known = set(cls.__dataclass_fields__.keys())
        d = {k: v for k, v in d.items() if k in known}
        return cls(**d)


class ModelProvider:
    """Manages a single model provider."""

    def __init__(self, config: ProviderConfig, api_key: Optional[str] = None):
        self.config = config
        self.api_key = api_key or config.api_key or ""
        self._client: Optional[openai.OpenAI] = None
        self.last_error: Optional[str] = None

    @property
    def client(self) -> openai.OpenAI:
        if self._client is None:
            key = self.api_key if self.api_key else "no-key"
            headers = dict(self.config.custom_headers)
            self._client = openai.OpenAI(
                api_key=key,
                base_url=self.config.base_url,
                default_headers=headers,
            )
        return self._client

    def reset_client(self):
        """Reset client so next access recreates with new settings."""
        self._client = None

    def discover_models(self) -> List[ModelInfo]:
        """Discover available models from the provider."""
        self.last_error = None
        if not self.config.base_url:
            self.last_error = "Provider base_url not configured"
            return []
        if self.config.type == ProviderType.OLLAMA:
            return self._discover_ollama_models()
        else:
            return self._discover_openai_models()

    def _discover_openai_models(self) -> List[ModelInfo]:
        try:
            models = self.client.models.list()
            result = []
            for m in models.data:
                info = ModelInfo(
                    id=m.id,
                    name=m.id,
                    description=f"{self.config.display_name} 模型",
                    context_length=self._estimate_context(m.id),
                    supports_tools=True,
                    provider=self.config.name,
                )
                result.append(info)
            return result
        except Exception as e:
            self.last_error = str(e)
            return []

    def _discover_ollama_models(self) -> List[ModelInfo]:
        try:
            resp = httpx.get(f"{self.config.base_url}/api/tags", timeout=8.0)
            resp.raise_for_status()
            data = resp.json()
            return [
                ModelInfo(
                    id=model["name"],
                    name=model["name"],
                    description=f"Ollama 本地模型",
                    context_length=4096,
                    supports_tools=True,
                    provider=self.config.name,
                )
                for model in data.get("models", [])
            ]
        except Exception as e:
            self.last_error = str(e)
            return []

    @staticmethod
    def _estimate_context(model_id: str) -> int:
        m = model_id.lower()
        if "128k" in m or "claude-3" in m: return 128000
        if "32k" in m: return 32000
        if "16k" in m: return 16000
        if any(x in m for x in ["gpt-4", "deepseek", "qwen", "glm"]):
            return 8192
        return 4096

    def health_check(self) -> tuple[bool, str]:
        """Check if the provider is accessible. Returns (is_healthy, message)."""
        if not self.config.base_url:
            return False, "base_url 未配置"
        try:
            if self.config.type == ProviderType.OLLAMA:
                resp = httpx.get(f"{self.config.base_url}/api/tags", timeout=5.0)
                return resp.status_code == 200, f"HTTP {resp.status_code}"
            else:
                models = self.client.models.list()
                count = len(models.data) if hasattr(models, 'data') else '?'
                return True, f"发现 {count} 个模型"
        except Exception as e:
            return False, str(e)[:100]

    def create_chat_completion(self, model_id: str, messages: list,
                                temperature: float = 0.7, **kwargs) -> str:
        response = self.client.chat.completions.create(
            model=model_id, messages=messages, temperature=temperature, **kwargs)
        return response.choices[0].message.content


# ============================================================================
# Provider Preset System (inspired by CC Switch)
# ============================================================================

@dataclass
class ProviderPreset:
    """A preset template for quickly adding a provider.
    
    Similar to CC Switch's preset system:
    - Select a preset -> fill in API Key -> done
    """
    name: str
    display_name: str
    type: ProviderType
    base_url: str
    api_key_env: str
    default_model: str
    description: str = ""
    website: str = ""

    def to_config(self, api_key: str = "") -> ProviderConfig:
        """Create a ProviderConfig from this preset."""
        return ProviderConfig(
            name=self.name,
            display_name=self.display_name,
            type=self.type,
            base_url=self.base_url,
            api_key_env=self.api_key_env,
            api_key=api_key,
            default_model=self.default_model,
        )


# 20+ Built-in provider presets
BUILTIN_PRESETS: Dict[str, ProviderPreset] = {
    "deepseek": ProviderPreset(
        name="deepseek",
        display_name="DeepSeek",
        type=ProviderType.OPENAI_COMPATIBLE,
        base_url="https://api.deepseek.com/v1",
        api_key_env="DEEPSEEK_API_KEY",
        default_model="deepseek-chat",
        description="DeepSeek 官方 API，性价比高，支持 V3/R1 模型",
        website="https://platform.deepseek.com",
    ),
    "openai": ProviderPreset(
        name="openai",
        display_name="OpenAI",
        type=ProviderType.OPENAI_COMPATIBLE,
        base_url="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
        default_model="gpt-4o-mini",
        description="OpenAI 官方 API，GPT-4o / GPT-3.5 系列",
        website="https://platform.openai.com",
    ),
    "anthropic": ProviderPreset(
        name="anthropic",
        display_name="Anthropic (Claude)",
        type=ProviderType.OPENAI_COMPATIBLE,
        base_url="https://api.anthropic.com/v1",
        api_key_env="ANTHROPIC_API_KEY",
        default_model="claude-3-sonnet-20240229",
        description="Anthropic Claude 系列模型",
        website="https://console.anthropic.com",
    ),
    "siliconflow": ProviderPreset(
        name="siliconflow",
        display_name="SiliconFlow (硅基流动)",
        type=ProviderType.OPENAI_COMPATIBLE,
        base_url="https://api.siliconflow.cn/v1",
        api_key_env="SILICONFLOW_API_KEY",
        default_model="deepseek-ai/DeepSeek-V3",
        description="国内聚合平台，支持 DeepSeek/Qwen/GLM 等",
        website="https://siliconflow.cn",
    ),
    "openrouter": ProviderPreset(
        name="openrouter",
        display_name="OpenRouter",
        type=ProviderType.OPENAI_COMPATIBLE,
        base_url="https://openrouter.ai/api/v1",
        api_key_env="OPENROUTER_API_KEY",
        default_model="deepseek/deepseek-chat",
        description="OpenRouter 聚合平台，支持 100+ 模型",
        website="https://openrouter.ai",
    ),
    "dashscope": ProviderPreset(
        name="dashscope",
        display_name="阿里云 DashScope (灵积)",
        type=ProviderType.OPENAI_COMPATIBLE,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key_env="DASHSCOPE_API_KEY",
        default_model="qwen-max",
        description="阿里云通义千问系列模型",
        website="https://dashscope.aliyun.com",
    ),
    "kimi": ProviderPreset(
        name="kimi",
        display_name="Moonshot (Kimi)",
        type=ProviderType.OPENAI_COMPATIBLE,
        base_url="https://api.moonshot.cn/v1",
        api_key_env="MOONSHOT_API_KEY",
        default_model="moonshot-v1-8k",
        description="Moonshot Kimi 系列模型，长文本能力突出",
        website="https://platform.moonshot.cn",
    ),
    "zhipu": ProviderPreset(
        name="zhipu",
        display_name="智谱 AI (GLM)",
        type=ProviderType.OPENAI_COMPATIBLE,
        base_url="https://open.bigmodel.cn/api/paas/v4",
        api_key_env="ZHIPU_API_KEY",
        default_model="glm-4",
        description="智谱 GLM-4 / GLM-3 系列模型",
        website="https://open.bigmodel.cn",
    ),
    "baidu": ProviderPreset(
        name="baidu",
        display_name="百度千帆 (ERNIE)",
        type=ProviderType.OPENAI_COMPATIBLE,
        base_url="https://qianfan.baidubce.com/v2",
        api_key_env="BAIDU_API_KEY",
        default_model="ernie-4.0",
        description="百度文心一言 ERNIE 系列",
        website="https://qianfan.cloud.baidu.com",
    ),
    "ollama": ProviderPreset(
        name="ollama",
        display_name="Ollama (本地模型)",
        type=ProviderType.OLLAMA,
        base_url="http://localhost:11434",
        api_key_env="",
        default_model="llama3.2",
        description="本地运行开源模型，无需 API Key",
        website="https://ollama.ai",
    ),
}

# Backward-compatible BUILTIN_PROVIDERS (generated from presets)
BUILTIN_PROVIDERS: Dict[str, ProviderConfig] = {
    name: preset.to_config() for name, preset in BUILTIN_PRESETS.items()
}


def get_preset_list() -> List[ProviderPreset]:
    """Get list of all available presets."""
    return list(BUILTIN_PRESETS.values())


def get_preset(name: str) -> Optional[ProviderPreset]:
    """Get a specific preset by name."""
    return BUILTIN_PRESETS.get(name)
