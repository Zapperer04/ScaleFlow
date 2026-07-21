import pytest
from unittest.mock import MagicMock, patch
import requests

from execution_engine.core.provider_session import ProviderSession
from execution_engine.data_plane.adapters.gemini_client import GeminiClient
from execution_engine.data_plane.adapters.openrouter_client import OpenRouterClient
from execution_engine.data_plane.adapters.gemini import GeminiAdapter
from execution_engine.data_plane.adapters.openrouter import OpenRouterAdapter
from execution_engine.core.artifact import ArtifactRef

# 1. ProviderSession Lifecycle Tests
def test_provider_session_lifecycle():
    session = ProviderSession(provider_id="gemini", trace_id="test-trace", retry_budget=2)
    assert session.provider_id == "gemini"
    assert session.trace_id == "test-trace"
    assert session.retry_budget == 2
    assert session.failure_layer is None
    
    session.record_duration("inference_time_ms", 1.5)
    assert session.metrics["inference_time_ms"] == 1500.0
    
    session.mark_failure("Schema", "Invalid JSON")
    assert session.failure_layer == "Schema"
    assert session.failure_reason == "Invalid JSON"
    assert session.metrics["total_time_ms"] > 0.0

# 2. GeminiClient Retry Logic Tests
@patch("requests.request")
def test_gemini_client_retry_success(mock_request):
    # Mocking first request as 502 Bad Gateway, second as 200 OK
    mock_resp_502 = MagicMock()
    mock_resp_502.status_code = 502
    
    mock_resp_200 = MagicMock()
    mock_resp_200.status_code = 200
    mock_resp_200.json.return_value = {
        "candidates": [{
            "finishReason": "STOP",
            "content": {"parts": [{"text": '{"nodes": []}'}]}
        }],
        "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 20}
    }
    
    mock_request.side_effect = [mock_resp_502, mock_resp_200]
    
    client = GeminiClient(api_key="fake-key", model="gemini-2.5-flash")
    parsed, in_tok, out_tok = client.generate_content("hello")
    
    assert parsed == {"nodes": []}
    assert in_tok == 10
    assert out_tok == 20
    assert mock_request.call_count == 2

@patch("requests.request")
def test_gemini_client_retry_exhausted(mock_request):
    mock_resp_500 = MagicMock()
    mock_resp_500.status_code = 500
    mock_request.return_value = mock_resp_500
    
    from execution_engine.data_plane.adapters.gemini_client import TransportError
    client = GeminiClient(api_key="fake-key", model="gemini-2.5-flash")
    with pytest.raises(TransportError):
        client.generate_content("hello")
        
    assert mock_request.call_count == 3

# 3. OpenRouterClient Retry Logic Tests
@patch("requests.request")
def test_openrouter_client_retry_success(mock_request):
    mock_resp_504 = MagicMock()
    mock_resp_504.status_code = 504
    
    mock_resp_200 = MagicMock()
    mock_resp_200.status_code = 200
    mock_resp_200.json.return_value = {
        "choices": [{"message": {"content": '{"nodes": []}'}}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 15}
    }
    
    mock_request.side_effect = [mock_resp_504, mock_resp_200]
    
    from execution_engine.data_plane.adapters.gemini_client import TransportError
    client = OpenRouterClient(api_key="fake-key", model="gemma")
    parsed, in_tok, out_tok = client.generate_content("hello")
    
    assert parsed == {"nodes": []}
    assert in_tok == 5
    assert out_tok == 15
    assert mock_request.call_count == 2

# 4. Adapter Parsing & Error Mapping Tests
@patch.object(GeminiClient, "upload_file")
@patch.object(GeminiClient, "generate_content")
def test_gemini_adapter_success(mock_generate, mock_upload):
    mock_upload.return_value = ("file-uri", "file-name")
    mock_generate.return_value = ({"nodes": [{"id": "n1"}]}, 50, 100)
    
    adapter = GeminiAdapter(api_key="fake-key")
    artifact = ArtifactRef(
        artifact_id="art-1",
        uri="file:///tmp/test.pdf",
        version="v1",
        content_type="application/pdf"
    )
    
    session = ProviderSession(provider_id="gemini", trace_id="trace")
    result = adapter.parse(artifact, {}, session=session)
    
    assert result == {"nodes": [{"id": "n1"}]}
    assert session.metrics["input_tokens"] == 50
    assert session.metrics["output_tokens"] == 100
    assert session.failure_layer is None

@patch.object(GeminiClient, "upload_file")
@patch.object(GeminiClient, "generate_content")
def test_gemini_adapter_malformed_json(mock_generate, mock_upload):
    mock_upload.return_value = ("file-uri", "file-name")
    mock_generate.side_effect = ValueError("Failed to parse Gemini JSON output")
    
    adapter = GeminiAdapter(api_key="fake-key")
    artifact = ArtifactRef(
        artifact_id="art-1",
        uri="file:///tmp/test.pdf",
        version="v1",
        content_type="application/pdf"
    )
    
    session = ProviderSession(provider_id="gemini", trace_id="trace")
    with pytest.raises(ValueError):
        adapter.parse(artifact, {}, session=session)
        
    assert session.failure_layer == "Schema"

@patch.object(GeminiClient, "upload_file")
@patch.object(GeminiClient, "generate_content")
def test_gemini_adapter_rate_limit(mock_generate, mock_upload):
    mock_upload.return_value = ("file-uri", "file-name")
    mock_generate.side_effect = Exception("API failure: status_code=429")
    
    adapter = GeminiAdapter(api_key="fake-key")
    artifact = ArtifactRef(
        artifact_id="art-1",
        uri="file:///tmp/test.pdf",
        version="v1",
        content_type="application/pdf"
    )
    
    session = ProviderSession(provider_id="gemini", trace_id="trace")
    with pytest.raises(Exception):
        adapter.parse(artifact, {}, session=session)
        
    assert session.failure_layer == "Provider"

@patch.object(GeminiClient, "upload_file")
@patch.object(GeminiClient, "generate_content")
def test_gemini_adapter_transport_error(mock_generate, mock_upload):
    mock_upload.side_effect = requests.ConnectionError("Connection timed out")
    
    adapter = GeminiAdapter(api_key="fake-key")
    artifact = ArtifactRef(
        artifact_id="art-1",
        uri="file:///tmp/test.pdf",
        version="v1",
        content_type="application/pdf"
    )
    
    session = ProviderSession(provider_id="gemini", trace_id="trace")
    with pytest.raises(requests.ConnectionError):
        adapter.parse(artifact, {}, session=session)
        
    assert session.failure_layer == "Transport"
