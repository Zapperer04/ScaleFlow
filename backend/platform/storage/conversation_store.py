import sqlite3
import json
from typing import List, Dict, Any, Optional

class ConversationStore:
    def __init__(self, db_conn: sqlite3.Connection):
        self.conn = db_conn

    def create_conversation(self, conversation_id: str, title: str):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO conversations (id, title) VALUES (?, ?)",
            (conversation_id, title)
        )
        self.conn.commit()

    def get_conversations(self) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, title, created_at FROM conversations ORDER BY created_at DESC")
        rows = cursor.fetchall()
        return [{"id": r["id"], "title": r["title"], "created_at": r["created_at"]} for r in rows]

    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, title, created_at FROM conversations WHERE id = ?", (conversation_id,))
        row = cursor.fetchone()
        if row:
            return {"id": row["id"], "title": row["title"], "created_at": row["created_at"]}
        return None

    def save_state(self, conversation_id: str, state_dict: Dict[str, Any]):
        cursor = self.conn.cursor()
        state_json = json.dumps(state_dict)
        cursor.execute("""
        INSERT INTO conversation_state (conversation_id, state_json, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(conversation_id) DO UPDATE SET
            state_json = excluded.state_json,
            updated_at = CURRENT_TIMESTAMP
        """, (conversation_id, state_json))
        self.conn.commit()

    def load_state(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT state_json FROM conversation_state WHERE conversation_id = ?", (conversation_id,))
        row = cursor.fetchone()
        if row:
            return json.loads(row["state_json"])
        return None

    def add_turn(self, conversation_id: str, user_message: str, assistant_message: str, citations: List[Dict[str, Any]], metrics: Dict[str, Any]):
        cursor = self.conn.cursor()
        cursor.execute("""
        INSERT INTO conversation_turns (conversation_id, user_message, assistant_message, citations_json, metrics_json)
        VALUES (?, ?, ?, ?, ?)
        """, (conversation_id, user_message, assistant_message, json.dumps(citations), json.dumps(metrics)))
        self.conn.commit()

    def get_turns(self, conversation_id: str) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("""
        SELECT user_message, assistant_message, citations_json, metrics_json, created_at
        FROM conversation_turns WHERE conversation_id = ? ORDER BY id ASC
        """, (conversation_id,))
        rows = cursor.fetchall()
        return [{
            "user_message": r["user_message"],
            "assistant_message": r["assistant_message"],
            "citations": json.loads(r["citations_json"]) if r["citations_json"] else [],
            "metrics": json.loads(r["metrics_json"]) if r["metrics_json"] else {},
            "created_at": r["created_at"]
        } for r in rows]
        
    def delete_conversation(self, conversation_id: str):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        cursor.execute("DELETE FROM conversation_state WHERE conversation_id = ?", (conversation_id,))
        cursor.execute("DELETE FROM conversation_turns WHERE conversation_id = ?", (conversation_id,))
        self.conn.commit()
