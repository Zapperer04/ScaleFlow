from backend.infrastructure.storage.base_storage import BaseBinaryStorage

class ArtifactStore:
    """Storage-agnostic artifact manager wrapping a BaseBinaryStorage instance."""

    def __init__(self, binary_storage: BaseBinaryStorage):
        self.binary_storage = binary_storage

    def save_artifact(self, storage_uri: str, data: bytes) -> None:
        self.binary_storage.save_bytes(storage_uri, data)

    def load_artifact(self, storage_uri: str) -> bytes:
        return self.binary_storage.load_bytes(storage_uri)

    def delete_artifact(self, storage_uri: str) -> None:
        self.binary_storage.delete(storage_uri)

    def health(self) -> dict:
        storage_health = self.binary_storage.health()
        return {
            "status": storage_health.get("status", "unknown"),
            "type": "artifact_store",
            "storage": storage_health
        }
