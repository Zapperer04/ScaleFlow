from typing import Dict, Any, Optional
from backend.platform.config.providers import MODEL_REGISTRY, PROVIDER_KEYS

class ProviderRegistry:
    def __init__(self):
        self.keys = PROVIDER_KEYS

    def get_provider_for_model(self, model: str) -> str:
        if model in MODEL_REGISTRY:
            return MODEL_REGISTRY[model]["primary"]
        return "openrouter"

    def get_fallbacks_for_model(self, model: str) -> list:
        if model in MODEL_REGISTRY:
            return MODEL_REGISTRY[model]["fallback"]
        return []

    def get_api_key(self, provider: str) -> str:
        return self.keys.get(provider, "")

provider_registry = ProviderRegistry()
