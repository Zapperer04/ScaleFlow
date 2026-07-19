from backend.infrastructure.providers.gemini_provider import GeminiProvider
from backend.infrastructure.providers.openrouter_provider import OpenRouterProvider
from backend.infrastructure.providers.ocr_provider import OCRProvider
from backend.infrastructure.providers.digital_pdf_provider import DigitalPDFProvider
from backend.infrastructure.providers.llamaparse_provider import LlamaParseProvider
from backend.infrastructure.providers.base_provider import BaseParserProvider

class ProviderFactory:
    @staticmethod
    def create_provider(provider_type: str) -> BaseParserProvider:
        p_type = provider_type.lower()
        if p_type == "gemini":
            return GeminiProvider()
        elif p_type == "openrouter":
            return OpenRouterProvider()
        elif p_type == "ocr":
            return OCRProvider()
        elif p_type == "digital_pdf":
            return DigitalPDFProvider()
        elif p_type == "llamaparse":
            return LlamaParseProvider()
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")
