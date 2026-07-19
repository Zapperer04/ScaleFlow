from backend.infrastructure.storage.base_storage import BaseBinaryStorage

class MemoryStorage(BaseBinaryStorage):
    """In-memory implementation of raw binary storage for testing and local fallback."""

    def __init__(self):
        self.files = {}

    def save_bytes(self, path: str, data: bytes) -> None:
        self.files[path] = data

    def load_bytes(self, path: str) -> bytes:
        if path not in self.files:
            raise FileNotFoundError(f"File not found in memory: {path}")
        return self.files[path]

    def delete(self, path: str) -> None:
        if path in self.files:
            del self.files[path]

    def exists(self, path: str) -> bool:
        return path in self.files

    def health(self) -> dict:
        return {"status": "healthy", "type": "memory", "file_count": len(self.files)}
