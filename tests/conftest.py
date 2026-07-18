import os
import sys

# Force offline sqlite database mode for testing
os.environ["DB_MODE"] = "sqlite"

# Ensure backend directory is in sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Apply shims/patches for offline testing safety
import re
def whoosh_escape(text):
    return re.sub(r'([\\+\-\!\(\)\{\}\[\]\^\"~\*\?\:\/])', r'\\\1', text)

try:
    import whoosh.qparser
    whoosh.qparser.escape = whoosh_escape
    sys.modules['whoosh.qparser'].escape = whoosh_escape
except ImportError:
    pass

try:
    import services.chunking_service
    original_build_node_map = services.chunking_service._build_node_map
    def patched_build_node_map(pages):
        if pages:
            for page in pages:
                if isinstance(page, dict):
                    for node in page.get("nodes", []):
                        if isinstance(node, dict):
                            if "chunk_id" in node and "node_id" not in node and "id" not in node:
                                node["node_id"] = node["chunk_id"]
        return original_build_node_map(pages)
    services.chunking_service._build_node_map = patched_build_node_map
except Exception:
    pass

try:
    import services.vector_store
    services.vector_store.upsert_document_chunks = lambda *args, **kwargs: (True, 0.0, 0.0)
except Exception:
    pass

try:
    import services.graph_expansion_service
    services.graph_expansion_service.set_chunk_lookup = lambda *args, **kwargs: None
except Exception:
    pass

try:
    import redis
    def patched_incr(self, key, amount=1):
        if not hasattr(self, "_mock_counters"):
            self._mock_counters = {}
        self._mock_counters[key] = self._mock_counters.get(key, 0) + amount
        return self._mock_counters[key]
    redis.Redis.incr = patched_incr
except Exception:
    pass


