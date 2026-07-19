import json
from typing import Any
from backend.infrastructure.storage.base_storage import BaseBinaryStorage

class ArtifactStore:
    """Storage-agnostic artifact manager wrapping a BaseBinaryStorage instance."""

    def __init__(self, binary_storage: BaseBinaryStorage):
        self.binary_storage = binary_storage

    # ------------------------------------------------------------------
    # Low-level binary API (bytes in / bytes out)
    # ------------------------------------------------------------------

    def save_artifact(self, storage_uri: str, data: bytes) -> None:
        self.binary_storage.save_bytes(storage_uri, data)

    def load_artifact(self, storage_uri: str) -> bytes:
        return self.binary_storage.load_bytes(storage_uri)

    def delete_artifact(self, storage_uri: str) -> None:
        self.binary_storage.delete(storage_uri)

    # ------------------------------------------------------------------
    # High-level typed API (serialize → store / load → deserialize)
    # Byte representation is byte-for-byte identical to the former
    # LegacyStorageAdapter implementation.
    # ------------------------------------------------------------------

    def save_artifact_data(self, storage_uri: str, data: Any) -> None:
        """Serialize *data* and persist it at *storage_uri*."""
        self.save_artifact(storage_uri, self._to_bytes(data))

    def load_artifact_data(self, storage_uri: str) -> Any:
        """Load bytes from *storage_uri* and deserialize them."""
        return self._from_bytes(self.load_artifact(storage_uri))

    # ------------------------------------------------------------------
    # Private serialization helpers
    # NOTE: These methods are the canonical owner of the serialization
    # contract previously held by LegacyStorageAdapter.  The logic MUST
    # remain byte-for-byte identical; do not rewrite or reorder.
    # ------------------------------------------------------------------

    @staticmethod
    def _to_bytes(data: Any) -> bytes:
        if isinstance(data, bytes):
            return data
        elif isinstance(data, (dict, list)):
            return json.dumps(data).encode("utf-8")
        else:
            return str(data).encode("utf-8")

    @staticmethod
    def _from_bytes(data_bytes: bytes) -> Any:
        try:
            return json.loads(data_bytes.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            try:
                return data_bytes.decode("utf-8")
            except UnicodeDecodeError:
                return data_bytes

    def health(self) -> dict:
        storage_health = self.binary_storage.health()
        return {
            "status": storage_health.get("status", "unknown"),
            "type": "artifact_store",
            "storage": storage_health
        }
