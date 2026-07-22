from typing import List, Dict, Any

class RetrievalSessionMemory:
    def __init__(self):
        # Maps session_id -> dict of past retrieval items
        self.sessions: Dict[str, Dict[str, Any]] = {}

    def get_memory(self, session_id: str) -> Dict[str, Any]:
        return self.sessions.get(session_id, {
            "chunk_ids": [],
            "node_ids": [],
            "entity_ids": [],
            "answers": []
        })

    def add_turn(self, session_id: str, chunk_ids: List[str], node_ids: List[str], entity_ids: List[str], answer: str):
        mem = self.get_memory(session_id)
        
        # Append and keep unique
        mem["chunk_ids"] = list(set(mem["chunk_ids"] + chunk_ids))
        mem["node_ids"] = list(set(mem["node_ids"] + node_ids))
        mem["entity_ids"] = list(set(mem["entity_ids"] + entity_ids))
        mem["answers"].append(answer)
        
        self.sessions[session_id] = mem
