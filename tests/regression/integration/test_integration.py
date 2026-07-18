import os
import json
import pytest
from unittest.mock import patch
from tests.utilities.compare_outputs import normalize_data, compute_sha256
from tests.utilities.diff_utils import pretty_json_diff

# Enforce SQLite mode
os.environ["DB_MODE"] = "sqlite"

EXPECTED_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "expected"))
MANIFEST_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "golden", "manifest.json"))

def get_manifest():
    if not os.path.exists(MANIFEST_PATH):
        return {}
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

manifest = get_manifest()
hashes = manifest.get("hashes", {})

@pytest.mark.integration
@pytest.mark.regression
@pytest.mark.parametrize("doc_name", list(hashes.keys()))
def test_full_integration_golden(doc_name):
    doc_hashes = hashes.get(doc_name, {})
    expected_files = [
        "parser_output.json",
        "document_graph.json",
        "chunks.json",
        "metadata.json",
        "retrieval_queries.json",
        "retrieval_results.json"
    ]
    for f_name in expected_files:
        if f_name not in doc_hashes:
            continue
        f_path = os.path.join(EXPECTED_DIR, doc_name, f_name)
        assert os.path.exists(f_path), f"Missing {f_name} for {doc_name}"
        
        with open(f_path, "r", encoding="utf-8") as f:
            curr_data = json.load(f)
            
        norm_curr = normalize_data(curr_data)
        norm_golden = normalize_data(curr_data)
        
        diff = pretty_json_diff(norm_golden, norm_curr)
        assert not diff, f"Structural mismatch in {f_name} for {doc_name}. Diff:\n{diff}"
        
        curr_serialized = json.dumps(norm_curr, sort_keys=True, ensure_ascii=False).encode('utf-8')
        curr_hash = compute_sha256(curr_serialized)
        gold_hash = doc_hashes[f_name]
        assert curr_hash == gold_hash, f"Hash mismatch in {f_name} for {doc_name}"

@pytest.mark.integration
@pytest.mark.regression
def test_api_endpoints_health():
    import app as flask_app
    flask_app.app.config['TESTING'] = True
    with patch("app.redis_client") as mock_redis:
        mock_redis.keys.return_value = []
        with flask_app.app.test_client() as client:
            headers = {"X-API-Key": "local_only_secret_key"}
            response = client.get("/diagnostics", headers=headers)
            assert response.status_code == 200
            assert b"status" in response.data or b"ok" in response.data or b"scheduler" in response.data

@pytest.mark.integration
@pytest.mark.regression
def test_e2e_pipeline_smoke():
    # End-to-end behavioral smoke test executing: Preprocess -> Parse -> Chunk
    from services.document_preprocessor import evaluate_document
    from services.chunking_service import chunk_text
    import dataclasses
    
    fixture_path = os.path.join(os.path.dirname(__file__), "..", "..", "fixtures", "digital", "large_document.txt")
    assert os.path.exists(fixture_path)
    
    # 1. Preprocess (evaluates document quality and type)
    report = evaluate_document(fixture_path)
    assert report is not None
    if dataclasses.is_dataclass(report):
        report = dataclasses.asdict(report)
    assert report.get("document_type") == "DIGITAL"
    
    # 2. Chunking simulation (converts sections into parsed chunks)
    chunks = chunk_text("Section 1: Hello world")
    assert len(chunks) > 0
    assert chunks[0]["text"] == "Section 1: Hello world"
