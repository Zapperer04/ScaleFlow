import os
import json
from typing import List, Dict, Any

class DatasetLoader:
    def __init__(self, filepath: str = None):
        if filepath is None:
            current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            filepath = os.path.join(current_dir, "evaluation", "metadata.json")
        self.filepath = filepath

    def load_questions(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.filepath):
            return []
        with open(self.filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("questions", [])
