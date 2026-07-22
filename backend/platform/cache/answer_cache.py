import hashlib
from typing import Dict, Any, Optional
from backend.platform.runtime.app_state import app_state

class AnswerCache:
    def __init__(self):
        self.category = "answer"

    def get_answer(self, query: str, context_hash: str) -> Optional[Dict[str, Any]]:
        if not app_state.cache_hierarchy:
            return None
        key = hashlib.sha256(f"{query}:{context_hash}".encode()).hexdigest()
        return app_state.cache_hierarchy.get(self.category, key)

    def cache_answer(self, query: str, context_hash: str, answer_data: Dict[str, Any]):
        if not app_state.cache_hierarchy:
            return
        key = hashlib.sha256(f"{query}:{context_hash}".encode()).hexdigest()
        app_state.cache_hierarchy.set(self.category, key, answer_data)
