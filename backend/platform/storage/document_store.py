import os
from backend.platform.config.settings import settings
from backend.platform.storage.object_storage import ObjectStorage

class DocumentStore:
    def __init__(self):
        self.storage = ObjectStorage()

    def store_document(self, document_id: str, filename: str, file_obj) -> str:
        key = f"{document_id}/{filename}"
        return self.storage.put_object("documents", key, file_obj)

    def get_document_path(self, document_id: str, filename: str) -> str:
        return self.storage.get_object_path("documents", f"{document_id}/{filename}")
