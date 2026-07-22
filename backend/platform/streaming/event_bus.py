from typing import Dict, List, Callable
from backend.platform.streaming.events import PlatformEvent

class EventBus:
    def __init__(self):
        self.listeners: Dict[str, List[Callable[[PlatformEvent], None]]] = {}

    def subscribe(self, event_type: str, callback: Callable[[PlatformEvent], None]):
        if event_type not in self.listeners:
            self.listeners[event_type] = []
        self.listeners[event_type].append(callback)

    def publish(self, event: PlatformEvent):
        # Notify specific listeners
        if event.event_type in self.listeners:
            for callback in self.listeners[event.event_type]:
                try:
                    callback(event)
                except Exception:
                    pass
        # Notify wildcard listeners
        if "*" in self.listeners:
            for callback in self.listeners["*"]:
                try:
                    callback(event)
                except Exception:
                    pass

event_bus = EventBus()
