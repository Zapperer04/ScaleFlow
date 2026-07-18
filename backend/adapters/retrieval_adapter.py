from typing import Dict, Any
from backend.domain.entities.retrieval import Retrieval
from backend.dto.retrieval import RetrievalRequestDTO, RetrievalResponseDTO

class RetrievalAdapter:
    @staticmethod
    def legacy_to_domain(legacy_dict: Dict[str, Any]) -> Retrieval:
        return Retrieval.from_dict(legacy_dict)

    @staticmethod
    def domain_to_legacy(domain_ret: Retrieval) -> Dict[str, Any]:
        return domain_ret.to_dict()

    @staticmethod
    def legacy_to_dto(legacy_dict: Dict[str, Any]) -> RetrievalResponseDTO:
        return RetrievalResponseDTO.model_validate(legacy_dict)

    @staticmethod
    def dto_to_legacy(dto: RetrievalResponseDTO) -> Dict[str, Any]:
        return dto.model_dump()
