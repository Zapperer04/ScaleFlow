import os
import json
import dataclasses
from typing import Any, Dict, Optional

class DocumentStore:
    def __init__(self, base_dir: str = None):
        if base_dir is None:
            # Place in task-schedular's storage/document_store
            current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.base_dir = os.path.join(current_dir, "storage", "document_store")
        else:
            self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def _get_doc_dir(self, document_id: str) -> str:
        return os.path.join(self.base_dir, document_id)

    def save_json(self, document_id: str, relative_path: str, data: Any):
        doc_dir = self._get_doc_dir(document_id)
        full_path = os.path.join(doc_dir, relative_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # Convert dataclasses to dicts recursively
        class EnhancedJSONEncoder(json.JSONEncoder):
            def default(self, o):
                if dataclasses.is_dataclass(o):
                    return dataclasses.asdict(o)
                return super().default(o)
                
        with open(full_path, "w", encoding="utf-8") as f:
            json.dump(data, f, cls=EnhancedJSONEncoder, indent=2, ensure_ascii=False)

    def load_json(self, document_id: str, relative_path: str) -> Optional[Any]:
        doc_dir = self._get_doc_dir(document_id)
        full_path = os.path.join(doc_dir, relative_path)
        if not os.path.exists(full_path):
            return None
        with open(full_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def exists(self, document_id: str, relative_path: str) -> bool:
        doc_dir = self._get_doc_dir(document_id)
        return os.path.exists(os.path.join(doc_dir, relative_path))
