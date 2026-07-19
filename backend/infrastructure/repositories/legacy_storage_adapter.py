import json
from typing import Any

class LegacyStorageAdapter:
    """Adapter to translate between legacy dict/string structures and binary storage bytes."""

    @staticmethod
    def to_bytes(data: Any) -> bytes:
        if isinstance(data, bytes):
            return data
        elif isinstance(data, (dict, list)):
            return json.dumps(data).encode("utf-8")
        else:
            return str(data).encode("utf-8")

    @staticmethod
    def from_bytes(data_bytes: bytes) -> Any:
        try:
            return json.loads(data_bytes.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            try:
                return data_bytes.decode("utf-8")
            except UnicodeDecodeError:
                return data_bytes
