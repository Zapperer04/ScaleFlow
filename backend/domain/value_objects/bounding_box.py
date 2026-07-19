from dataclasses import dataclass
from backend.domain.exceptions.exceptions import ValidationError

@dataclass(frozen=True)
class BoundingBox:
    x0: float
    y0: float
    x1: float
    y1: float

    def __post_init__(self):
        for val in (self.x0, self.y0, self.x1, self.y1):
            if not isinstance(val, (int, float)):
                raise ValidationError(f"BoundingBox coordinates must be numeric: {val}")
        if self.x0 > self.x1 or self.y0 > self.y1:
            raise ValidationError(f"Invalid BoundingBox dimensions: x0={self.x0}, x1={self.x1}, y0={self.y0}, y1={self.y1}")

    def to_dict(self):
        return [self.x0, self.y0, self.x1, self.y1]

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, list) or len(data) != 4:
            raise ValidationError("BoundingBox must be a list of 4 floats/ints")
        return cls(x0=float(data[0]), y0=float(data[1]), x1=float(data[2]), y1=float(data[3]))
