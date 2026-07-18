from dataclasses import dataclass
from typing import Dict, Any, Optional
from backend.domain.value_objects.page_number import PageNumber

@dataclass(frozen=True)
class Page:
    page_number: PageNumber
    text: str
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_number": self.page_number.to_dict(),
            "text": self.text,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Page":
        return cls(
            page_number=PageNumber.from_dict(data["page_number"]),
            text=data["text"],
            metadata=data.get("metadata", {}),
        )
