from typing import Dict, Any, Optional
from backend.platform.runtime.app_state import app_state

class SessionCache:
    def __init__(self):
        self.category = "session"

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        if not app_state.cache_hierarchy:
            return None
        return app_state.cache_hierarchy.get(self.category, session_id)

    def cache_session(self, session_id: str, state: Dict[str, Any]):
        if not app_state.cache_hierarchy:
            return
        app_state.cache_hierarchy.set(self.category, session_id, state)

    def delete_session(self, session_id: str):
        if not app_state.cache_hierarchy:
            return
        app_state.cache_hierarchy.delete(self.category, session_id)
