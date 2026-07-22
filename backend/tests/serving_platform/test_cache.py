import sys
import os
import pytest
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from backend.platform.cache.hierarchy import CacheHierarchy
from backend.platform.cache.retrieval_cache import RetrievalCache
from backend.platform.runtime.app_state import app_state
from backend.platform.config.settings import settings

@pytest.fixture
def temp_cache_dir():
    temp_dir = tempfile.mkdtemp()
    original_cache_dir = settings.CACHE_DIR
    settings.CACHE_DIR = temp_dir
    
    hierarchy = CacheHierarchy()
    app_state.cache_hierarchy = hierarchy
    
    yield hierarchy
    
    app_state.cache_hierarchy = None
    settings.CACHE_DIR = original_cache_dir
    shutil.rmtree(temp_dir)

def test_cache_hierarchy_and_retrieval_cache(temp_cache_dir):
    hierarchy = temp_cache_dir
    
    # 1. Test basic get/set
    hierarchy.set("answer", "key1", {"text": "hello"})
    val = hierarchy.get("answer", "key1")
    assert val == {"text": "hello"}
    
    # 2. Test Retrieval Cache
    ret_cache = RetrievalCache()
    query = "what is RAG?"
    params = {"top_k": 3}
    candidates = [{"chunk_id": "c1", "text": "Retrieval Augmented Gen"}]
    
    # Cache Context
    ret_cache.cache_context(query_embedding=None, query_text=query, params=params, candidates=candidates)
    
    # Retrieve Context
    hit = ret_cache.get_context(query_embedding=None, query_text=query, params=params)
    assert hit == candidates
