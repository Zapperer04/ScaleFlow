import os
import json
import pytest
from tests.utilities.compare_outputs import normalize_data, compute_sha256
from tests.utilities.diff_utils import pretty_json_diff
from services.document_preprocessor import evaluate_document

EXPECTED_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "expected"))
FIXTURES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "fixtures"))
MANIFEST_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "golden", "manifest.json"))

FIXTURE_MAP = {
    "digital_large_document": "digital/large_document.txt",
    "forms_large_document": "forms/large_document.txt",
    "images_large_document": "images/large_document.txt",
    "mixed_large_document": "mixed/large_document.txt",
    "multicolumn_large_document": "multicolumn/large_document.txt",
    "scanned_large_document": "scanned/large_document.txt",
    "tables_large_document": "tables/large_document.txt",
}

def get_manifest():
    if not os.path.exists(MANIFEST_PATH):
        return {}
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

manifest = get_manifest()
hashes = manifest.get("hashes", {})

@pytest.mark.parser
@pytest.mark.regression
@pytest.mark.parametrize("doc_name", list(FIXTURE_MAP.keys()))
def test_parser_golden_regression(doc_name):
    # Execute actual document evaluation on the raw fixture
    fixture_rel = FIXTURE_MAP[doc_name]
    fixture_path = os.path.join(FIXTURES_DIR, fixture_rel)
    assert os.path.exists(fixture_path), f"Fixture missing at {fixture_path}"
    
    # 1. Execute the production code
    fresh_report = evaluate_document(fixture_path)
    import dataclasses
    if dataclasses.is_dataclass(fresh_report):
        fresh_report = dataclasses.asdict(fresh_report)
    
    # 2. Load golden output
    golden_file = os.path.join(EXPECTED_DIR, doc_name, "parser_output.json")
    assert os.path.exists(golden_file), f"Golden file missing at {golden_file}"
    with open(golden_file, "r", encoding="utf-8") as f:
        golden_data = json.load(f)
        
    # 3. Normalize both
    norm_fresh = normalize_data(fresh_report)
    norm_golden = normalize_data(golden_data)
    
    # 4. Compare structures first (as requested by User)
    diff = pretty_json_diff(norm_golden, norm_fresh)
    assert not diff, f"Structural mismatch for {doc_name}. Diff:\n{diff}"
    
    # 5. Check hash consistency (as requested by User)
    fresh_serialized = json.dumps(norm_fresh, sort_keys=True, ensure_ascii=False).encode('utf-8')
    fresh_hash = compute_sha256(fresh_serialized)
    golden_serialized = json.dumps(norm_golden, sort_keys=True, ensure_ascii=False).encode('utf-8')
    golden_hash = compute_sha256(golden_serialized)
    assert fresh_hash == golden_hash, f"Hash mismatch for {doc_name}: fresh={fresh_hash}, golden={golden_hash}"

@pytest.mark.parser
@pytest.mark.regression
def test_parser_unsupported_format():
    from services.pdf_parser import parse_pdf
    with pytest.raises(Exception):
        parse_pdf("nonexistent.xyz", None)
