from typing import Optional, Any
import logging

logger = logging.getLogger(__name__)

class AppState:
    def __init__(self):
        self.db_conn: Optional[Any] = None
        self.queue: Optional[Any] = None
        self.worker: Optional[Any] = None
        self.metrics: Optional[Any] = None
        self.tracer: Optional[Any] = None
        self.cache_hierarchy: Optional[Any] = None
        
        # In-memory session registries
        self.active_websockets = []
        self.active_chats_count = 0
        
    def is_healthy(self) -> bool:
        if self.db_conn is None:
            return False
        if self.queue is None:
            return False
        return True

app_state = AppState()
