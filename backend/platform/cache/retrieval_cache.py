import hashlib
import json
from typing import List, Dict, Any, Optional
from backend.platform.runtime.app_state import app_state

class RetrievalCache:
    def __init__(self):
        self.category = "retrieval"

    def _compute_key(self, query_embedding: Optional[List[float]], query_text: str, params: Dict[str, Any]) -> str:
        # If query_embedding is present, serialize and hash it
        if query_embedding:
            emb_str = ",".join(map(str, query_embedding))
            emb_hash = hashlib.sha256(emb_str.encode()).hexdigest()
        else:
            emb_hash = hashlib.sha256(query_text.encode()).hexdigest()
            
        params_hash = hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()
        return f"{emb_hash}:{params_hash}"

    def get_context(self, query_embedding: Optional[List[float]], query_text: str, params: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        if not app_state.cache_hierarchy:
            return None
        key = self._compute_key(query_embedding, query_text, params)
        return app_state.cache_hierarchy.get(self.category, key)

    def cache_context(self, query_embedding: Optional[List[float]], query_text: str, params: Dict[str, Any], candidates: List[Dict[str, Any]]):
        if not app_state.cache_hierarchy:
            return
        key = self._compute_key(query_embedding, query_text, params)
        app_state.cache_hierarchy.set(self.category, key, candidates)
