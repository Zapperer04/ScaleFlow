import os
import json
import pytest
from services.document_preprocessor import evaluate_document
from tests.utilities.compare_outputs import normalize_data
from tests.utilities.diff_utils import pretty_json_diff

FIXTURES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "fixtures"))

FIXTURES = [
    "digital/large_document.txt",
    "scanned/large_document.txt",
    "mixed/large_document.txt"
]

@pytest.mark.determinism
@pytest.mark.parametrize("fixture_rel", FIXTURES)
def test_determinism_twice(fixture_rel):
    fixture_path = os.path.join(FIXTURES_DIR, fixture_rel)
    assert os.path.exists(fixture_path), f"Fixture missing at {fixture_path}"
    
    # Run 1
    report1 = evaluate_document(fixture_path)
    # Run 2
    report2 = evaluate_document(fixture_path)
    
    import dataclasses
    if dataclasses.is_dataclass(report1):
        report1 = dataclasses.asdict(report1)
    if dataclasses.is_dataclass(report2):
        report2 = dataclasses.asdict(report2)
        
    # Normalize
    norm1 = normalize_data(report1)
    norm2 = normalize_data(report2)
    
    # Compare
    diff = pretty_json_diff(norm1, norm2)
    assert not diff, f"Nondeterministic run detected for {fixture_rel}. Diff:\n{diff}"
