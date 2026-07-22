from typing import List, Optional
from backend.platform.runtime.app_state import app_state

class EmbeddingCache:
    def __init__(self):
        self.category = "embedding"

    def get_embedding(self, text: str) -> Optional[List[float]]:
        if app_state.cache_hierarchy:
            return app_state.cache_hierarchy.get(self.category, text)
        return None

    def cache_embedding(self, text: str, embedding: List[float]):
        if app_state.cache_hierarchy:
            app_state.cache_hierarchy.set(self.category, text, embedding)
