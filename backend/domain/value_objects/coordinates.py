from dataclasses import dataclass
from backend.domain.exceptions.exceptions import ValidationError

@dataclass(frozen=True)
class Coordinates:
    x: float
    y: float

    def __post_init__(self):
        for val in (self.x, self.y):
            if not isinstance(val, (int, float)):
                raise ValidationError(f"Coordinates must be numeric: {val}")

    def to_dict(self):
        return {"x": self.x, "y": self.y}

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict) or "x" not in data or "y" not in data:
            raise ValidationError("Coordinates must be a dict with 'x' and 'y'")
        return cls(x=float(data["x"]), y=float(data["y"]))
