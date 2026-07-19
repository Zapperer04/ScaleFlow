import time
from typing import Any, Callable, Dict, Optional
from backend.infrastructure.providers.base_provider import BaseParserProvider
from backend.infrastructure.providers.metrics import ProviderMetrics
from services.pdf_parser import ParseResult

class LlamaParseProvider(BaseParserProvider):
    def __init__(self):
        self.metrics = ProviderMetrics()

    def parse_document(
        self,
        filepath: str,
        task_id: Optional[str] = None,
        lease_token: Optional[str] = None,
        progress_json: Optional[dict] = None,
        trace_fn: Optional[Callable[[str], None]] = None,
        api_url: Optional[str] = None,
        api_headers: Optional[dict] = None,
        skip_ocr: bool = False,
        document_type: str = "MULTIMODAL",
        routing_confidence: float = 1.0,
        parse_method_hint: str = "vlm_document_graph",
        enhanced_pages_path: Optional[str] = None,
        on_page_completed: Optional[Callable[[int, Dict[str, Any]], None]] = None,
    ) -> ParseResult:
        raise NotImplementedError("LlamaParseProvider is a stub and is not implemented yet.")

    def health(self) -> bool:
        return False

    def supports_pdf(self) -> bool:
        return True

    def supports_images(self) -> bool:
        return True

    def supports_batch(self) -> bool:
        return False

    def max_pages(self) -> int:
        return 0

    def max_tokens(self) -> int:
        return 0

    def availability(self) -> float:
        return 0.0
