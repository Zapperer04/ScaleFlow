import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from backend.platform.streaming.events import PlatformEvent, EVENT_PAGE_PARSED
from backend.platform.streaming.token_stream import TokenStreamFormatter
from backend.platform.streaming.event_bus import EventBus

def test_event_bus_and_sse_formatting():
    # 1. Test Event Bus PubSub
    bus = EventBus()
    received_events = []
    
    def listener(event: PlatformEvent):
        received_events.append(event)
        
    bus.subscribe(EVENT_PAGE_PARSED, listener)
    
    event = PlatformEvent(EVENT_PAGE_PARSED, {"page": 1, "pct": 20.0})
    bus.publish(event)
    
    assert len(received_events) == 1
    assert received_events[0].event_type == EVENT_PAGE_PARSED
    assert received_events[0].data["page"] == 1
    
    # 2. Test SSE Formatter
    sse_line = TokenStreamFormatter.format_sse(EVENT_PAGE_PARSED, {"page": 1})
    assert sse_line.startswith("data: ")
    assert EVENT_PAGE_PARSED in sse_line
