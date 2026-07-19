from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional
from backend.domain.aggregates.document import Document

class ParsingService(ABC):
    """Application Service interface for orchestrating document parsing."""
    @abstractmethod
    def parse_document(self, file_path: str) -> Document:
        """Parse document and return Domain model representation."""
        pass


class ParsingServiceImpl(ParsingService):
    def __init__(
        self,
        parser_provider: Any,
        checkpoint_service: Any = None,
        graph_builder: Any = None,
        validator: Any = None,
    ):
        self.parser_provider = parser_provider
        self.checkpoint_service = checkpoint_service
        self.graph_builder = graph_builder
        self.validator = validator

    def parse_document(
        self,
        file_path: str,
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
    ) -> Document:
        """Parse document using the injected provider/router and return Domain representation."""
        provider = self.parser_provider
        if hasattr(provider, "route"):
            provider = provider.route(document_type=document_type)

        result = provider.parse_document(
            filepath=file_path,
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

        from backend.adapters.parser_adapter import ParserAdapter
        import os
        filename = os.path.basename(file_path)

        # Build metadata dict carrying both domain data and raw parser outputs.
        # document_graph and stats are parser-layer outputs (not domain entities)
        # and are stored here for downstream worker pipeline consumption.
        # pages (raw list) and domain pages (Page entities) are separated:
        #   - Document.pages  : typed domain Page entities (via ParserAdapter)
        #   - metadata["pages"]: raw list from the parser provider
        legacy_report = {
            "document_type": document_type,
            "pages": result.pages,
            "timings": result.stats.get("timings", {}) if result.stats else {},
            "document_graph": result.document_graph,
            "stats": result.stats,
            "metadata": result.stats,
        }
        domain_doc = ParserAdapter.legacy_to_domain(legacy_report, filename, 1)

        # Augment metadata with raw parser outputs so the worker can retrieve
        # them without relying on CompatibleDocument legacy attributes.
        metadata = dict(domain_doc.metadata)
        metadata["document_graph"] = result.document_graph
        metadata["stats"] = result.stats
        metadata["pages"] = result.pages

        return Document(
            document_id=domain_doc.document_id,
            filename=domain_doc.filename,
            pages=domain_doc.pages,
            chunks=domain_doc.chunks,
            graph=domain_doc.graph,
            metadata=metadata,
            artifacts=domain_doc.artifacts,
        )
