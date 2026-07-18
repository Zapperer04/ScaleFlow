import os
from typing import Any, Callable, Dict, Optional
from services.pdf_parser import parse_pdf, ParseResult
from services.gemini_rate_manager import RateLimitPauseRequired

class BaseVLMProvider:
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
        raise NotImplementedError

class GeminiVLMProvider(BaseVLMProvider):
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
        os.environ["VLM_PROVIDER"] = "gemini"
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
        )

class OpenRouterProvider(BaseVLMProvider):
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
        os.environ["VLM_PROVIDER"] = "openrouter"
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
        )

def get_vlm_provider() -> BaseVLMProvider:
    provider_name = os.getenv("VLM_PROVIDER", "openrouter").lower()
    if provider_name == "gemini":
        return GeminiVLMProvider()
    return OpenRouterProvider()
