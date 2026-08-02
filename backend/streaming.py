import json
import time
from typing import Generator, List, Dict, Any

def format_sse(event: str, data: Any) -> str:
    """Formats event name and payload into Server Sent Events string format"""
    json_data = json.dumps(data)
    return f"event: {event}\ndata: {json_data}\n\n"

def stream_answer_generator(
    answer: str,
    citations: List[Dict[str, Any]],
    trace_id: str,
    delay: float = 0.05
) -> Generator[str, None, None]:
    """
    Yields SSE-compliant string blocks for answer generation.
    Sends:
      - event: delta (containing chunk of characters/tokens)
      - event: citation (containing citation details)
      - event: complete (indicating stream has finished)
    """
    # 1. Stream the text word-by-word or character-by-character
    words = answer.split(" ")
    for idx, word in enumerate(words):
        space = " " if idx < len(words) - 1 else ""
        delta_payload = {
            "text": f"{word}{space}",
            "trace_id": trace_id
        }
        yield format_sse("delta", delta_payload)
        time.sleep(delay)
        
    # 2. Stream the citations
    for cit in citations:
        citation_payload = {
            "citation": cit,
            "trace_id": trace_id
        }
        yield format_sse("citation", citation_payload)
        time.sleep(0.1)

    # 3. Stream completion event
    yield format_sse("complete", {"trace_id": trace_id, "done": True})
