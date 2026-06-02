import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from services.pdf_parser import parse_pdf

class TestResourceLimits(unittest.TestCase):
    def setUp(self):
        # Save original limit
        self.original_char_limit = config.MAX_CHARACTER_LIMIT
        
    def tearDown(self):
        # Restore original limit
        config.MAX_CHARACTER_LIMIT = self.original_char_limit

    def test_character_limit_guard_triggered(self):
        # Set limit to an extremely low value to trigger early abort
        config.MAX_CHARACTER_LIMIT = 50
        
        pdf_path = os.path.join(os.path.dirname(__file__), "test_data", "category_A_simple.pdf")
        if not os.path.exists(pdf_path):
            # Fallback path if run from project root
            pdf_path = "backend/test_data/category_A_simple.pdf"
            
        print(f"Testing character limit guard on PDF: {pdf_path}")
        self.assertTrue(os.path.exists(pdf_path), f"Test PDF does not exist at {pdf_path}")
        
        # Verify that parsing raises ValueError with Governance Limit Exceeded message
        with self.assertRaises(ValueError) as context:
            parse_pdf(pdf_path)
            
        error_msg = str(context.exception)
        print(f"Caught expected exception: {error_msg}")
        self.assertIn("Governance Limit Exceeded", error_msg)
        self.assertIn("exceeded limit", error_msg)

if __name__ == "__main__":
    unittest.main()
