import os
import sys
import time
import unittest
import threading
import redis

# Add backend dir to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.gemini_rate_manager import GeminiRateManager
from services.document_preprocessor import GeminiRateLimitError, execute_vlm_document_graph_extraction

from PIL import Image

def create_mock_image(filename="page_mock.png"):
    img = Image.new("RGB", (800, 600), color="white")
    img.filename = filename
    return img

class TestRateLimitResumable(unittest.TestCase):
    def setUp(self):
        # Reset rate manager state
        self.rate_mgr = GeminiRateManager()
        self.rate_mgr._set_value("cooldown_until", 0.0)
        self.rate_mgr._set_value("backoff_level", 0)
        self.rate_mgr._set_value("requests_sent", 0)
        self.rate_mgr._set_value("429_count", 0)
        self.rate_mgr._set_value("total_pause_duration", 0.0)

    def test_rate_manager_cooldown(self):
        """Test that registering 429 sets cooldown and check_availability returns false."""
        available, remaining = self.rate_mgr.check_availability()
        self.assertTrue(available)
        self.assertEqual(remaining, 0.0)

        # Trigger 429 with 5 seconds cooldown hint
        wait_time = self.rate_mgr.register_429(retry_after_header="5")
        self.assertEqual(wait_time, 5.0)

        available, remaining = self.rate_mgr.check_availability()
        self.assertFalse(available)
        self.assertTrue(remaining > 0.0)

    def test_exponential_backoff_fallback(self):
        """Test that when Retry-After header is missing, rate manager does exponential backoff."""
        # 1st 429: backoff level 1
        wait_1 = self.rate_mgr.register_429(retry_after_header=None)
        # 5 * (1.5^0) * jitter -> 5 * 1 * [0.5, 2.0] -> [2.5, 10.0]
        self.assertTrue(2.5 <= wait_1 <= 10.0)

        # 2nd 429: backoff level 2
        wait_2 = self.rate_mgr.register_429(retry_after_header=None)
        # 5 * (1.5^1) * jitter -> 7.5 * [0.5, 2.0] -> [3.75, 15.0]
        self.assertTrue(3.75 <= wait_2 <= 15.0)

        # Success clears backoff level
        self.rate_mgr.register_success()
        level = self.rate_mgr._get_value("backoff_level", 0)
        self.assertEqual(level, 0)

    def test_resumable_parsing_mock(self):
        """Test that execute_vlm_document_graph_extraction skips already completed pages."""
        # Create a progress_json representing pages 1 and 2 already processed
        progress_json = {
            "parser": "gemini",
            "completed_pages": [1, 2],
            "completed_pages_data": {
                "1": {
                    "page_number": 1,
                    "source": "gemini",
                    "nodes": [{"chunk_id": "p1_n1", "text": "Mock page 1 content"}],
                    "edges": []
                },
                "2": {
                    "page_number": 2,
                    "source": "gemini",
                    "nodes": [{"chunk_id": "p2_n1", "text": "Mock page 2 content"}],
                    "edges": []
                }
            }
        }

        # Mock images
        images = [create_mock_image("1.png"), create_mock_image("2.png"), create_mock_image("3.png")]
        
        # Track completed pages callbacks
        completed_callbacks = []
        def on_page_completed(page_num, page_res):
            completed_callbacks.append(page_num)

        # We will parse only page 3. Since page 1 and 2 are in progress_json,
        # we will expect that page 3 is the only one run by preprocessor.
        # But wait, to prevent actual Gemini API calls in test, we will mock _call_gemini_page_parser
        # or use OCR fallback for page 3 by setting the parser choice to "ocr" via progress_json lock.
        progress_json["parser"] = "ocr"

        from unittest.mock import patch
        mock_ocr_data = {
            "page_number": 3,
            "source": "ocr",
            "nodes": [{"chunk_id": "p3_n1", "text": "Mock page 3 content"}],
            "edges": []
        }
        
        with patch("services.document_preprocessor._ocr_fallback_page", return_value=mock_ocr_data):
            graph = execute_vlm_document_graph_extraction(
                images=images,
                pipeline_id="test-pipeline",
                max_workers=1,
                progress_json=progress_json,
                on_page_completed=on_page_completed
            )

        self.assertIsNotNone(graph)
        # Check that page 1 and 2 were reused from progress_json, and only page 3 was parsed and invoked callback
        self.assertEqual(len(graph["pages"]), 3)
        self.assertEqual(completed_callbacks, [3])
        
        # Verify page 1 and 2 text contents are preserved
        p1_nodes = graph["pages"][0]["nodes"]
        self.assertEqual(p1_nodes[0]["text"], "Mock page 1 content")

if __name__ == "__main__":
    unittest.main()
