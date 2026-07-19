from typing import Dict, List, Optional
from backend.infrastructure.providers.base_provider import BaseParserProvider

class ProviderRegistry:
    def __init__(self):
        self._providers: Dict[str, BaseParserProvider] = {}
        self._enabled: Dict[str, bool] = {}

    def register(self, name: str, provider: BaseParserProvider, enabled: bool = True):
        name_lower = name.lower()
        self._providers[name_lower] = provider
        self._enabled[name_lower] = enabled

    def get(self, name: str) -> Optional[BaseParserProvider]:
        name_lower = name.lower()
        if name_lower in self._providers and self._enabled.get(name_lower, False):
            return self._providers[name_lower]
        return None

    def enable(self, name: str):
        name_lower = name.lower()
        if name_lower in self._providers:
            self._enabled[name_lower] = True

    def disable(self, name: str):
        name_lower = name.lower()
        if name_lower in self._providers:
            self._enabled[name_lower] = False

    def list_all(self) -> Dict[str, BaseParserProvider]:
        return {name: p for name, p in self._providers.items()}

    def find_by_capability(
        self,
        pdf: Optional[bool] = None,
        images: Optional[bool] = None,
        batch: Optional[bool] = None,
        filter_healthy: bool = True,
    ) -> List[tuple[str, BaseParserProvider]]:
        results = []
        for name, provider in self._providers.items():
            if not self._enabled.get(name, False):
                continue
            if filter_healthy and not provider.health():
                continue
            if pdf is not None and provider.supports_pdf() != pdf:
                continue
            if images is not None and provider.supports_images() != images:
                continue
            if batch is not None and provider.supports_batch() != batch:
                continue
            results.append((name, provider))
        return results
