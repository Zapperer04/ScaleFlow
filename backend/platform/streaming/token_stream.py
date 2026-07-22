import json
from typing import Dict, Any

class TokenStreamFormatter:
    @staticmethod
    def format_sse(event_type: str, data: Dict[str, Any]) -> str:
        payload = json.dumps({
            "event": event_type,
            "data": data
        })
        return f"data: {payload}\n\n"
