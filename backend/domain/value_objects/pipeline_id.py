from dataclasses import dataclass
from backend.domain.exceptions.exceptions import ValidationError

@dataclass(frozen=True)
class PipelineId:
    value: int

    def __post_init__(self):
        if not isinstance(self.value, int) or self.value <= 0:
            raise ValidationError(f"Invalid PipelineId: {self.value}")

    def to_dict(self):
        return self.value

    @classmethod
    def from_dict(cls, data):
        return cls(value=int(data))
