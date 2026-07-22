from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class ConversationState:
    active_document_ids: List[str] = field(default_factory=list)
    active_sections: List[str] = field(default_factory=list)
    active_entities: List[str] = field(default_factory=list)
    active_tables: List[str] = field(default_factory=list)
    active_graph_nodes: List[str] = field(default_factory=list)
    unresolved_questions: List[str] = field(default_factory=list)
    previous_answers: List[str] = field(default_factory=list)
    chunk_ids: List[str] = field(default_factory=list)

class RetrievalSessionMemory:
    def __init__(self):
        # Maps session_id -> ConversationState
        self.sessions: Dict[str, ConversationState] = {}

    def get_memory(self, session_id: str) -> ConversationState:
        if session_id not in self.sessions:
            self.sessions[session_id] = ConversationState()
        return self.sessions[session_id]

    def add_turn(
        self, 
        session_id: str, 
        chunk_ids: List[str], 
        node_ids: List[str], 
        entity_ids: List[str], 
        answer: str,
        document_id: str = None,
        sections: List[str] = None,
        tables: List[str] = None,
        query: str = None
    ):
        state = self.get_memory(session_id)
        
        # Append and keep unique
        state.chunk_ids = list(set(state.chunk_ids + chunk_ids))
        state.active_graph_nodes = list(set(state.active_graph_nodes + node_ids))
        state.active_entities = list(set(state.active_entities + entity_ids))
        
        if document_id:
            state.active_document_ids = list(set(state.active_document_ids + [document_id]))
        if sections:
            state.active_sections = list(set(state.active_sections + sections))
        if tables:
            state.active_tables = list(set(state.active_tables + tables))
        if query:
            state.unresolved_questions.append(query)
        if answer:
            state.previous_answers.append(answer)
        
        self.sessions[session_id] = state
