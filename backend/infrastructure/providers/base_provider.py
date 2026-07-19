from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional
from services.pdf_parser import ParseResult

class BaseParserProvider(ABC):
    @abstractmethod
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
        """Parse the document and return a ParseResult."""
        pass

    @abstractmethod
    def health(self) -> bool:
        """Return True if the provider is healthy/available."""
        pass

    @abstractmethod
    def supports_pdf(self) -> bool:
        """Return True if the provider supports PDF parsing."""
        pass

    @abstractmethod
    def supports_images(self) -> bool:
        """Return True if the provider supports image/OCR parsing."""
        pass

    @abstractmethod
    def supports_batch(self) -> bool:
        """Return True if the provider supports batching/parallel processing."""
        pass

    @abstractmethod
    def max_pages(self) -> int:
        """Return the maximum number of pages this provider can handle in a single document."""
        pass

    @abstractmethod
    def max_tokens(self) -> int:
        """Return the maximum tokens limit of the model if applicable."""
        pass

    @abstractmethod
    def availability(self) -> float:
        """Return a float between 0.0 and 1.0 representing historical or current availability score."""
        pass
