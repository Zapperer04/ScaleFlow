from typing import Dict, Any
from backend.domain.entities.embedding import Embedding
from backend.dto.embedding import EmbeddingDTO

class EmbeddingAdapter:
    @staticmethod
    def legacy_to_domain(legacy_dict: Dict[str, Any]) -> Embedding:
        return Embedding.from_dict(legacy_dict)

    @staticmethod
    def domain_to_legacy(domain_emb: Embedding) -> Dict[str, Any]:
        return domain_emb.to_dict()

    @staticmethod
    def legacy_to_dto(legacy_dict: Dict[str, Any]) -> EmbeddingDTO:
        return EmbeddingDTO.model_validate(legacy_dict)

    @staticmethod
    def dto_to_legacy(dto: EmbeddingDTO) -> Dict[str, Any]:
        return dto.model_dump()
