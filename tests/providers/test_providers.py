import pytest
import time
from unittest.mock import MagicMock, patch

pytestmark = [pytest.mark.regression]

from backend.infrastructure.providers.base_provider import BaseParserProvider
from backend.infrastructure.providers.gemini_provider import GeminiProvider, VLMCompatibilityAdapter
from backend.infrastructure.providers.openrouter_provider import OpenRouterProvider
from backend.infrastructure.providers.ocr_provider import OCRProvider
from backend.infrastructure.providers.digital_pdf_provider import DigitalPDFProvider
from backend.infrastructure.providers.llamaparse_provider import LlamaParseProvider
from backend.infrastructure.providers.provider_registry import ProviderRegistry
from backend.infrastructure.providers.provider_router import ProviderRouter
from backend.infrastructure.providers.retry_policy import RetryPolicy
from backend.infrastructure.providers.circuit_breaker import CircuitBreaker, CircuitBreakerOpenException
from backend.infrastructure.providers.bootstrap import bootstrap_app
from backend.application.parsing_service import ParsingServiceImpl, CompatibleDocument
from services.pdf_parser import ParseResult

# ------------------------------------------------------------------------------
# 1. Base / Compatibility / Metrics Tests
# ------------------------------------------------------------------------------
def test_vlm_compatibility_adapter():
    import os
    # Ensure starting state
    os.environ.pop("VLM_PROVIDER", None)
    
    with VLMCompatibilityAdapter("test_val"):
        assert os.environ.get("VLM_PROVIDER") == "test_val"
    
    assert "VLM_PROVIDER" not in os.environ

# ------------------------------------------------------------------------------
# 2. Retry Policy Tests
# ------------------------------------------------------------------------------
def test_retry_policy_success():
    call_count = 0
    def dummy_func():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("Transient error")
        return "Success"

    policy = RetryPolicy(max_retries=3, initial_delay=0.01, backoff_factor=1.0)
    retry_recorded = 0
    def on_retry():
        nonlocal retry_recorded
        retry_recorded += 1

    res = policy.execute(dummy_func, on_retry_cb=on_retry)
    assert res == "Success"
    assert call_count == 3
    assert retry_recorded == 2

def test_retry_policy_exhaustion():
    def dummy_func():
        raise ValueError("Permanent error")

    policy = RetryPolicy(max_retries=2, initial_delay=0.01, backoff_factor=1.0)
    with pytest.raises(ValueError):
        policy.execute(dummy_func)

# ------------------------------------------------------------------------------
# 3. Circuit Breaker Tests
# ------------------------------------------------------------------------------
def test_circuit_breaker_flow():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.05)
    
    # 1. Successful executes
    assert cb.execute(lambda: "OK") == "OK"
    assert cb.state == "CLOSED"
    
    # 2. Failure threshold hit
    with pytest.raises(ValueError):
        cb.execute(lambda: raise_val_error())
    assert cb.state == "CLOSED" # 1 failure
    
    with pytest.raises(ValueError):
        cb.execute(lambda: raise_val_error())
    assert cb.state == "OPEN" # 2 failures -> Open

    # 3. Open state fast failure
    with pytest.raises(CircuitBreakerOpenException):
        cb.execute(lambda: "OK")

    # 4. Wait for recovery timeout -> HALF-OPEN
    time.sleep(0.06)
    # Success in half-open -> CLOSED
    assert cb.execute(lambda: "OK") == "OK"
    assert cb.state == "CLOSED"

def raise_val_error():
    raise ValueError("Error")

# ------------------------------------------------------------------------------
# 4. Registry Tests
# ------------------------------------------------------------------------------
def test_provider_registry():
    registry = ProviderRegistry()
    gemini = GeminiProvider()
    ocr = OCRProvider()

    registry.register("gemini", gemini)
    registry.register("ocr", ocr, enabled=False)

    assert registry.get("gemini") == gemini
    assert registry.get("ocr") is None # Disabled

    registry.enable("ocr")
    assert registry.get("ocr") == ocr

    registry.disable("gemini")
    assert registry.get("gemini") is None

# ------------------------------------------------------------------------------
# 5. Router & Capability Matching Tests
# ------------------------------------------------------------------------------
def test_provider_router():
    registry = ProviderRegistry()
    gemini = GeminiProvider()
    ocr = OCRProvider()
    digital = DigitalPDFProvider()

    registry.register("gemini", gemini)
    registry.register("ocr", ocr)
    registry.register("digital_pdf", digital)

    router = ProviderRouter(registry)

    # Scanned -> Gemini preferred
    routed = router.route(document_type="SCANNED", page_count=5)
    assert routed == gemini

    # Digital -> Digital PDF preferred
    routed = router.route(document_type="DIGITAL", page_count=5)
    assert routed == digital

    # Huge page count -> Gemini has page limit 1000, digital has 2000, ocr has 100
    routed = router.route(document_type="DIGITAL", page_count=1500)
    assert routed == digital

# ------------------------------------------------------------------------------
# 6. Dependency Injection / Parsing Service Mock Tests
# ------------------------------------------------------------------------------
@patch("backend.infrastructure.providers.gemini_provider.parse_pdf")
def test_parsing_service_with_injected_provider(mock_parse_pdf):
    # Set mock response
    mock_parse_pdf.return_value = ParseResult(
        document_graph={"nodes": [], "edges": []},
        stats={"node_count": 0},
        pages=[{"page": 1, "text": "Page 1 Content"}]
    )

    container = bootstrap_app()
    # Override provider in registry to control test
    provider = container.registry.get("gemini")
    assert provider is not None

    # Execute service call
    doc = container.parsing_service.parse_document(
        file_path="dummy.pdf",
        document_type="SCANNED"
    )

    assert isinstance(doc, CompatibleDocument)
    assert doc.stats == {"node_count": 0}
    # verify __getattribute__ returns raw pages when pages is accessed
    assert len(doc.pages) == 1
    assert doc.pages[0]["text"] == "Page 1 Content"
