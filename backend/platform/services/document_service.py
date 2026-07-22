import os
import sqlite3
from typing import List, Dict, Any, Optional
from backend.platform.storage.document_store import DocumentStore

class DocumentService:
    def __init__(self, db_conn: sqlite3.Connection, store: DocumentStore):
        self.conn = db_conn
        self.store = store

    def register_document(self, document_id: str, filename: str, filepath: str) -> Dict[str, Any]:
        cursor = self.conn.cursor()
        # Initial state is UPLOADED
        state = "UPLOADED"
        cursor.execute("""
        INSERT OR IGNORE INTO documents (id, filename, filepath, state)
        VALUES (?, ?, ?, ?)
        """, (document_id, filename, filepath, state))
        self.conn.commit()
        
        cursor.execute("SELECT * FROM documents WHERE id = ?", (document_id,))
        return dict(cursor.fetchone())

    def update_state(self, document_id: str, state: str, versions: Dict[str, str] = None):
        cursor = self.conn.cursor()
        if versions:
            cursor.execute("""
            UPDATE documents SET 
                state = ?,
                parser_version = ?,
                embedding_version = ?,
                chunk_version = ?,
                graph_version = ?,
                index_version = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """, (
                state,
                versions.get("parser_version"),
                versions.get("embedding_version"),
                versions.get("chunk_version"),
                versions.get("graph_version"),
                versions.get("index_version"),
                document_id
            ))
        else:
            cursor.execute("""
            UPDATE documents SET state = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?
            """, (state, document_id))
        self.conn.commit()

    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE id = ?", (document_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def list_documents(self) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM documents ORDER BY created_at DESC")
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

    def delete_document(self, document_id: str) -> bool:
        cursor = self.conn.cursor()
        doc = self.get_document(document_id)
        if not doc:
            return False
            
        # Update state to DELETED
        self.update_state(document_id, "DELETED")
        
        # Remove physical file if exists
        try:
            if os.path.exists(doc["filepath"]):
                os.remove(doc["filepath"])
        except Exception:
            pass
            
        cursor.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        self.conn.commit()
        return True

    def check_and_lock_document(self, document_id: str) -> bool:
        """
        Check if document is already being indexed to avoid concurrent parsing tasks.
        Returns True if locked/available, False if already busy indexing.
        """
        doc = self.get_document(document_id)
        if doc and doc["state"] == "INDEXING":
            return False
        return True
