from dataclasses import dataclass
from backend.domain.exceptions.exceptions import ValidationError

@dataclass(frozen=True)
class ChunkId:
    value: str

    def __post_init__(self):
        if not isinstance(self.value, str) or not self.value.strip():
            raise ValidationError(f"Invalid ChunkId: {self.value}")

    def to_dict(self):
        return self.value

    @classmethod
    def from_dict(cls, data):
        return cls(value=str(data))
