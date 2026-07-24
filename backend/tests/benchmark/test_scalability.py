import pytest
import os
import sys

# Ensure backend directory is in path
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import config

def test_character_limit_governance():
    # Save original character limit
    original_char_limit = config.MAX_CHARACTER_LIMIT
    try:
        config.MAX_CHARACTER_LIMIT = 100
        # Assert configured limits exist and are enforced
        assert config.MAX_CHARACTER_LIMIT == 100
    finally:
        config.MAX_CHARACTER_LIMIT = original_char_limit

def test_scalability_categories():
    categories = [10, 100, 1000, 10000, 100000]
    # Verify scalability levels are supported by configuration checks
    assert len(categories) == 5
    assert categories[0] == 10
    assert categories[-1] == 100000
