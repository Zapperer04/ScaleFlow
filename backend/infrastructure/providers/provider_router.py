from typing import Optional
from backend.infrastructure.providers.provider_registry import ProviderRegistry
from backend.infrastructure.providers.base_provider import BaseParserProvider

class ProviderRouter:
    def __init__(self, registry: ProviderRegistry):
        self.registry = registry

    def route(
        self,
        document_type: str = "MULTIMODAL",
        page_count: int = 1,
        preferred_provider_name: Optional[str] = None,
    ) -> BaseParserProvider:
        # 1. If a preferred provider is specified and exists/enabled/healthy, use it.
        if preferred_provider_name:
            provider = self.registry.get(preferred_provider_name)
            if provider and provider.health() and page_count <= provider.max_pages():
                return provider

        # 2. Map routing strategy based on document_type
        doc_type_upper = document_type.upper()
        
        # Priority list of provider names to try
        if doc_type_upper == "DIGITAL":
            candidates = ["digital_pdf", "gemini", "openrouter", "ocr"]
        elif doc_type_upper == "SCANNED":
            candidates = ["gemini", "openrouter", "ocr"]
        else: # MULTIMODAL or fallback
            candidates = ["gemini", "openrouter", "ocr"]

        # Find the first healthy candidate within page limits
        for name in candidates:
            provider = self.registry.get(name)
            if provider and provider.health():
                # Check page limits if provider specifies them (max_pages > 0)
                max_pg = provider.max_pages()
                if max_pg <= 0 or page_count <= max_pg:
                    return provider

        # Fallback to anything enabled and healthy
        healthy_providers = self.registry.find_by_capability(filter_healthy=True)
        if healthy_providers:
            return healthy_providers[0][1]

        # Desperate fallback: try to get any provider by candidate order even if unhealthy
        for name in candidates:
            provider = self.registry.get(name)
            if provider:
                return provider

        # Ultimate fallback: return a default OCR provider
        default_ocr = self.registry.get("ocr")
        if default_ocr:
            return default_ocr

        raise RuntimeError("No parser providers registered in ProviderRegistry.")
