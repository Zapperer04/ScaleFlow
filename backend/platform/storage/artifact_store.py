import os
import json
from typing import Any
from backend.platform.config.settings import settings
from engine.document_pipeline.storage.storage import DocumentStore as EngineDocStore

class ArtifactStore:
    """
    Interfaces with the engine's artifact storage folder and manages representations on disk.
    """
    def __init__(self):
        # We reuse the engine's storage implementation base directory
        self.engine_store = EngineDocStore(base_dir=settings.ARTIFACTS_DIR)

    def get_engine_store(self) -> EngineDocStore:
        return self.engine_store

    def save_json(self, doc_id: str, filepath: str, data: Any):
        self.engine_store.save_json(doc_id, filepath, data)

    def load_json(self, doc_id: str, filepath: str) -> Any:
        return self.engine_store.load_json(doc_id, filepath)

    def exists(self, doc_id: str, filepath: str) -> bool:
        return self.engine_store.exists(doc_id, filepath)
