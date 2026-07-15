import os
from typing import Any, Callable, Dict, Optional
from abc import ABC, abstractmethod

from services.pdf_parser import parse_pdf, ParseResult


class BaseVLMProvider(ABC):
    """
    Abstract base class for all VLM (Vision Language Model) providers.

    This interface defines the contract between the parsing pipeline and
    external VLM services. Each provider must implement the core
    ``parse_document`` method, and may override optional methods like
    ``health_check``, ``supports_pdf``, and ``supports_images``.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique identifier for this provider (e.g., 'gemini', 'openrouter')."""
        pass

    @property
    def is_remote(self) -> bool:
        """
        Indicates whether the provider makes outbound network requests.

        Default is True.  Local providers (e.g., Tesseract, Nougat) should
        override to return False for offline or local-only processing.
        """
        return True

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
        """
        Parse a document using the provider.

        All parameters are passed through to the underlying parser.  This method
        should not be called directly by external code; use the factory function
        ``get_vlm_provider()`` to obtain a concrete instance.

        Returns:
            ParseResult: The parsing result containing extracted content and metadata.
        """
        raise NotImplementedError

    def health_check(self) -> bool:
        """
        Verify that the provider is ready to accept requests.

        Default implementation returns True; subclasses should override to
        check for required API keys or network connectivity.

        Returns:
            bool: True if the provider is considered healthy, False otherwise.
        """
        return True

    def supports_pdf(self) -> bool:
        """Return True if this provider can process PDF documents."""
        return True

    def supports_images(self) -> bool:
        """Return True if this provider can process image documents."""
        return True


class _VLMProviderWithEnv(BaseVLMProvider):
    """
    Internal base class that implements ``parse_document`` by setting the
    ``VLM_PROVIDER`` environment variable and forwarding all arguments to the
    shared ``parse_pdf`` function.

    This is a compatibility layer that preserves the existing behavior of the
    global parser, which reads the provider name from the environment.  All
    concrete providers that rely on this mechanism should inherit from this
    class and only need to define the ``provider_name`` property.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

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
        # Set the environment variable that the global parser uses to select
        # the VLM backend.  This is necessary because we cannot change the
        # signature of parse_pdf to accept the provider explicitly without
        # breaking other parts of the codebase.
        os.environ["VLM_PROVIDER"] = self.provider_name
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


class GeminiVLMProvider(_VLMProviderWithEnv):
    """Concrete VLM provider for Google's Gemini models."""

    @property
    def provider_name(self) -> str:
        return "gemini"

    def health_check(self) -> bool:
        # Gemini requires the GEMINI_API_KEY environment variable.
        return bool(os.getenv("GEMINI_API_KEY"))


class OpenRouterProvider(_VLMProviderWithEnv):
    """Concrete VLM provider for OpenRouter's aggregated model API."""

    @property
    def provider_name(self) -> str:
        return "openrouter"

    def health_check(self) -> bool:
        # OpenRouter requires the OPENROUTER_API_KEY environment variable.
        return bool(os.getenv("OPENROUTER_API_KEY"))


class LlamaParseProvider(BaseVLMProvider):
    """
    Stub provider for LlamaParse (LlamaIndex's document parsing service).

    This class is a placeholder to demonstrate future extensibility.  The
    actual implementation will be added when the LlamaParse integration is
    fully developed.
    """

    @property
    def provider_name(self) -> str:
        return "llamaparse"

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
        raise RuntimeError(
            "LlamaParse integration has not yet been implemented. "
            "Please use 'gemini' or 'openrouter'."
        )

    def health_check(self) -> bool:
        # LlamaParse would require LLAMAPARSE_API_KEY; stub checks for it.
        return bool(os.getenv("LLAMAPARSE_API_KEY"))

    def supports_pdf(self) -> bool:
        # Stub: assume it will support PDFs in the future.
        return True

    def supports_images(self) -> bool:
        # Stub: assume it will support images in the future.
        return True


# Provider registry: maps provider names to their classes.
# Adding a new provider requires only inserting an entry here.
_PROVIDER_REGISTRY = {
    "gemini": GeminiVLMProvider,
    "openrouter": OpenRouterProvider,
    "llamaparse": LlamaParseProvider,
}


def get_vlm_provider(provider_name: Optional[str] = None) -> BaseVLMProvider:
    """
    Factory function that returns a concrete VLM provider instance.

    If no provider name is given, the value of the environment variable
    ``VLM_PROVIDER`` is used (defaulting to 'openrouter').  Supported names
    are the keys of ``_PROVIDER_REGISTRY``.

    Args:
        provider_name: Optional explicit provider name.  If omitted, reads
                       from the environment.

    Returns:
        BaseVLMProvider: An instance of the requested provider.

    Raises:
        ValueError: If the provider name is not supported.
    """
    if provider_name is None:
        provider_name = os.getenv("VLM_PROVIDER", "openrouter").lower()

    try:
        provider_class = _PROVIDER_REGISTRY[provider_name]
    except KeyError:
        supported = ", ".join(f"'{k}'" for k in _PROVIDER_REGISTRY.keys())
        raise ValueError(
            f"Unsupported VLM provider: '{provider_name}'. "
            f"Supported providers are: {supported}."
        )

    return provider_class()