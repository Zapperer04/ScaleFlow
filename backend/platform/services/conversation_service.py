import uuid
from typing import List, Dict, Any, Optional
from backend.platform.storage.conversation_store import ConversationStore

class ConversationService:
    def __init__(self, store: ConversationStore):
        self.store = store

    def start_conversation(self, title: str) -> str:
        conversation_id = str(uuid.uuid4())
        self.store.create_conversation(conversation_id, title)
        return conversation_id

    def list_conversations(self) -> List[Dict[str, Any]]:
        return self.store.get_conversations()

    def get_conversation_history(self, conversation_id: str) -> List[Dict[str, Any]]:
        return self.store.get_turns(conversation_id)

    def record_turn(self, conversation_id: str, user_message: str, assistant_message: str, citations: List[Any], metrics: Any):
        # Format citations
        serialized_citations = []
        for c in citations:
            serialized_citations.append({
                "source": c.get("source", ""),
                "score": c.get("score", 0.0),
                "text": c.get("text", "")
            })
            
        # Format metrics
        serialized_metrics = {
            "prompt_tokens": getattr(metrics, "prompt_tokens", 0),
            "completion_tokens": getattr(metrics, "completion_tokens", 0),
            "generation_time": getattr(metrics, "generation_time", 0.0),
            "verification_time": getattr(metrics, "verification_time", 0.0),
            "llm_cost": getattr(metrics, "llm_cost", 0.0),
            "citation_count": getattr(metrics, "citation_count", 0),
            "hallucination_rate": getattr(metrics, "hallucination_rate", 0.0),
            "retry_count": getattr(metrics, "retry_count", 0),
            "provider": getattr(metrics, "provider", "unknown"),
            "model": getattr(metrics, "model", "unknown")
        }
        
        self.store.add_turn(conversation_id, user_message, assistant_message, serialized_citations, serialized_metrics)

    def persist_session_state(self, conversation_id: str, session_memory: Any):
        state = session_memory.get_memory(conversation_id)
        state_dict = {
            "active_document_ids": state.active_document_ids,
            "active_sections": state.active_sections,
            "active_entities": state.active_entities,
            "active_tables": state.active_tables,
            "active_graph_nodes": state.active_graph_nodes,
            "unresolved_questions": state.unresolved_questions,
            "previous_answers": state.previous_answers,
            "chunk_ids": state.chunk_ids
        }
        self.store.save_state(conversation_id, state_dict)

    def recover_session_state(self, conversation_id: str, session_memory: Any) -> bool:
        state_dict = self.store.load_state(conversation_id)
        if not state_dict:
            return False
            
        state = session_memory.get_memory(conversation_id)
        state.active_document_ids = state_dict.get("active_document_ids", [])
        state.active_sections = state_dict.get("active_sections", [])
        state.active_entities = state_dict.get("active_entities", [])
        state.active_tables = state_dict.get("active_tables", [])
        state.active_graph_nodes = state_dict.get("active_graph_nodes", [])
        state.unresolved_questions = state_dict.get("unresolved_questions", [])
        state.previous_answers = state_dict.get("previous_answers", [])
        state.chunk_ids = state_dict.get("chunk_ids", [])
        
        session_memory.sessions[conversation_id] = state
        return True
        
    def delete_conversation(self, conversation_id: str):
        self.store.delete_conversation(conversation_id)
