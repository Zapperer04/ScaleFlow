from dataclasses import dataclass
from typing import List
from backend.domain.exceptions.exceptions import ValidationError

@dataclass(frozen=True)
class EmbeddingVector:
    values: List[float]

    def __post_init__(self):
        if not isinstance(self.values, list):
            raise ValidationError("EmbeddingVector must be a list of floats")
        for val in self.values:
            if not isinstance(val, (int, float)):
                raise ValidationError(f"EmbeddingVector element must be numeric: {val}")

    def to_dict(self):
        return self.values

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, list):
            raise ValidationError("EmbeddingVector data must be a list")
        return cls(values=[float(x) for x in data])
