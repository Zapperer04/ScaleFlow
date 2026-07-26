import time
from typing import Any, Callable, Dict, Optional
from backend.infrastructure.providers.base_provider import BaseParserProvider
from backend.infrastructure.providers.metrics import ProviderMetrics
from backend.infrastructure.providers.retry_policy import RetryPolicy
from backend.infrastructure.providers.circuit_breaker import CircuitBreaker
from services.pdf_parser import execute_vlm_parse, ParseResult


class OpenRouterProvider(BaseParserProvider):
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
        skip_ocr: bool = False,
        document_type: str = "MULTIMODAL",
        routing_confidence: float = 1.0,
        parse_method_hint: str = "vlm_document_graph",
        enhanced_pages_path: Optional[str] = None,
        on_page_completed: Optional[Callable[[int, Dict[str, Any]], None]] = None,
    ) -> ParseResult:
        start_time = time.time()

        def run_parsing():
            document_graph, page_metadata, vlm_duration, vlm_mb, total_pages = execute_vlm_parse(
                filepath=filepath,
                vlm_provider_name="openrouter",
                task_id=task_id,
                progress_json=progress_json,
                trace_fn=trace_fn,
                on_page_completed=on_page_completed,
            )

            if not document_graph:
                raise RuntimeError("VLM parsing returned empty results")

            total_nodes = sum(len(pg.get("nodes", [])) for pg in document_graph.get("pages", []))
            total_edges = len(document_graph.get("edges", []))
            processed_pages = len(document_graph.get("pages", []))

            stats = {
                "parser": "openrouter_vlm",
                "total_pages": total_pages,
                "processed_pages": processed_pages,
                "vlm_pages": processed_pages,
                "ocr_pages": 0,
                "failed_pages": total_pages - processed_pages,
                "node_count": total_nodes,
                "edge_count": total_edges,
                "duration_seconds": time.time() - start_time,
                "memory_peak_mb": vlm_mb,
                "timings": {
                    "rendering_duration": 0.0,
                    "vlm_extraction_duration": vlm_duration,
                    "ocr_fallback_duration": 0.0,
                    "total_duration": time.time() - start_time,
                }
            }
            return ParseResult(
                document_graph=document_graph,
                stats=stats,
                pages=page_metadata
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
        return True

    def supports_batch(self) -> bool:
        return False  # OpenRouter has single batch cap in document_preprocessor

    def max_pages(self) -> int:
        return 500

    def max_tokens(self) -> int:
        return 1000000

    def availability(self) -> float:
        return 0.98 if self.health() else 0.0
