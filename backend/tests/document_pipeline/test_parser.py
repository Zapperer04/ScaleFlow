import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.document_pipeline.parser.parser import VLMParser

TEST_PDF_PATH = "test_data/category_A_simple.pdf"

def test_vlm_parser_fallback_mode():
    os.environ["TEST_OFFLINE_MODE"] = "True"
    parser = VLMParser()
    res = parser.parse(TEST_PDF_PATH)
    assert res is not None
    assert "document_path" in res
    assert "total_pages" in res
    assert "pages" in res
    assert len(res["pages"]) > 0
    assert res["parser_used"] == "pypdf_fallback"

def test_vlm_parser_invalid_file():
    parser = VLMParser()
    with pytest.raises(FileNotFoundError):
        parser.parse("non_existent_file.pdf")
