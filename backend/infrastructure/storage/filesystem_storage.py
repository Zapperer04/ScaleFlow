import os
from backend.infrastructure.storage.base_storage import BaseBinaryStorage

class FilesystemStorage(BaseBinaryStorage):
    """Filesystem implementation of raw binary storage."""

    def __init__(self, base_dir: str):
        self.base_dir = os.path.abspath(base_dir)

    def _full_path(self, path: str) -> str:
        # Normalize and split logic matching legacy splits
        normalized = path.replace("\\", "/")
        if "storage/" in normalized:
            rel_path = normalized.split("storage/", 1)[1]
        else:
            rel_path = normalized
        return os.path.normpath(os.path.join(self.base_dir, rel_path))

    def save_bytes(self, path: str, data: bytes) -> None:
        full_path = self._full_path(path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "wb") as f:
            f.write(data)

    def load_bytes(self, path: str) -> bytes:
        full_path = self._full_path(path)
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"File not found at: {full_path}")
        with open(full_path, "rb") as f:
            return f.read()

    def delete(self, path: str) -> None:
        full_path = self._full_path(path)
        if os.path.exists(full_path):
            os.remove(full_path)

    def exists(self, path: str) -> bool:
        full_path = self._full_path(path)
        return os.path.exists(full_path)

    def health(self) -> dict:
        try:
            os.makedirs(self.base_dir, exist_ok=True)
            # Try a dummy write/read/delete
            test_path = os.path.join(self.base_dir, ".health_probe")
            with open(test_path, "w") as f:
                f.write("ok")
            os.remove(test_path)
            return {"status": "healthy", "type": "filesystem", "base_dir": self.base_dir}
        except Exception as e:
            return {"status": "unhealthy", "type": "filesystem", "error": str(e)}
