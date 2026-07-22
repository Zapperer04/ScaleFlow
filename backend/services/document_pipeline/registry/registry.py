import os
import sqlite3
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

class DocumentRegistry:
    def __init__(self, db_path: str = None):
        if db_path is None:
            current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            db_path = os.path.join(current_dir, "storage", "document_store", "registry.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS registry (
                    document_id TEXT PRIMARY KEY,
                    versions TEXT,
                    hashes TEXT,
                    dependencies TEXT,
                    available_representations TEXT,
                    builder_outputs TEXT,
                    created_at TEXT,
                    last_updated TEXT
                )
            """)
            conn.commit()

    def register_document(
        self,
        document_id: str,
        versions: Dict[str, str],
        hashes: Dict[str, str],
        dependencies: Dict[str, List[str]],
        available_representations: List[str],
        builder_outputs: Dict[str, Any]
    ):
        now = datetime.utcnow().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT created_at FROM registry WHERE document_id = ?", (document_id,))
            row = cursor.fetchone()
            created_at = row[0] if row else now

            cursor.execute("""
                INSERT OR REPLACE INTO registry 
                (document_id, versions, hashes, dependencies, available_representations, builder_outputs, created_at, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                document_id,
                json.dumps(versions),
                json.dumps(hashes),
                json.dumps(dependencies),
                json.dumps(available_representations),
                json.dumps(builder_outputs),
                created_at,
                now
            ))
            conn.commit()

    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM registry WHERE document_id = ?", (document_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "document_id": row["document_id"],
                "versions": json.loads(row["versions"]),
                "hashes": json.loads(row["hashes"]),
                "dependencies": json.loads(row["dependencies"]) if row["dependencies"] else {},
                "available_representations": json.loads(row["available_representations"]),
                "builder_outputs": json.loads(row["builder_outputs"]),
                "created_at": row["created_at"],
                "last_updated": row["last_updated"]
            }

    def list_documents(self) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM registry")
            rows = cursor.fetchall()
            res = []
            for row in rows:
                res.append({
                    "document_id": row["document_id"],
                    "versions": json.loads(row["versions"]),
                    "hashes": json.loads(row["hashes"]),
                    "dependencies": json.loads(row["dependencies"]) if row["dependencies"] else {},
                    "available_representations": json.loads(row["available_representations"]),
                    "builder_outputs": json.loads(row["builder_outputs"]),
                    "created_at": row["created_at"],
                    "last_updated": row["last_updated"]
                })
            return res
