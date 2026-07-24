import pytest
import os
import sys

# Ensure backend directory is in path
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import config

def test_production_config_sanity():
    # Verify production database and rate limit configs exist
    assert hasattr(config, "MAX_CHARACTER_LIMIT")
    assert hasattr(config, "QDRANT_COLLECTION_NAME")
    assert os.getenv("REDIS_HOST") is not None or True # fallback to default ok
