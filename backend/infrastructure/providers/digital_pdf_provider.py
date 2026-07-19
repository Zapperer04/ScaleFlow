import time
from typing import Any, Callable, Dict, Optional
from backend.infrastructure.providers.base_provider import BaseParserProvider
from backend.infrastructure.providers.metrics import ProviderMetrics
from backend.infrastructure.providers.retry_policy import RetryPolicy
from backend.infrastructure.providers.circuit_breaker import CircuitBreaker
from services.pdf_parser import parse_pdf, ParseResult

class DigitalPDFProvider(BaseParserProvider):
    def __init__(self):
        self.metrics = ProviderMetrics()
        self.retry_policy = RetryPolicy(max_retries=3)
        self.circuit_breaker = CircuitBreaker()

    def parse_document(
        self,
        filepath: str,
        task_id: Optional[str] = None,
        lease_token: Optional[str] = None,
        progress_json: Optional[dict] = None,
        trace_fn: Optional[Callable[[str], None]] = None,
        api_url: Optional[str] = None,
        api_headers: Optional[dict] = None,
        skip_ocr: bool = True, # For digital PDF, skip OCR by default
        document_type: str = "DIGITAL",
        routing_confidence: float = 1.0,
        parse_method_hint: str = "vlm_document_graph",
        enhanced_pages_path: Optional[str] = None,
        on_page_completed: Optional[Callable[[int, Dict[str, Any]], None]] = None,
    ) -> ParseResult:
        start_time = time.time()

        def run_parsing():
            return parse_pdf(
                filepath=filepath,
                task_id=task_id,
                lease_token=lease_token,
                progress_json=progress_json,
                trace_fn=trace_fn,
                api_url=api_url,
                api_headers=api_headers,
                skip_ocr=skip_ocr,
                document_type=document_type,
                routing_confidence=routing_confidence,
                parse_method_hint=parse_method_hint,
                enhanced_pages_path=enhanced_pages_path,
                on_page_completed=on_page_completed,
                vlm_provider_name="digital_pdf",
            )

        try:
            result = self.circuit_breaker.execute(
                lambda: self.retry_policy.execute(run_parsing, on_retry_cb=self.metrics.record_retry)
            )
            pages = len(result.pages) if result.pages else 0
            self.metrics.record_success(pages=pages, latency=time.time() - start_time)
            return result
        except Exception as e:
            self.metrics.record_failure(latency=time.time() - start_time)
            raise e

    def health(self) -> bool:
        return self.circuit_breaker.state != "OPEN"

    def supports_pdf(self) -> bool:
        return True

    def supports_images(self) -> bool:
        return False

    def supports_batch(self) -> bool:
        return True

    def max_pages(self) -> int:
        return 2000

    def max_tokens(self) -> int:
        return 0

    def availability(self) -> float:
        return 1.0 if self.health() else 0.0
