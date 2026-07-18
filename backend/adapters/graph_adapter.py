from typing import Dict, Any
from backend.domain.entities.graph import Graph
from backend.dto.graph import GraphDTO

class GraphAdapter:
    @staticmethod
    def legacy_to_domain(legacy_dict: Dict[str, Any]) -> Graph:
        return Graph.from_dict(legacy_dict)

    @staticmethod
    def domain_to_legacy(domain_graph: Graph) -> Dict[str, Any]:
        return domain_graph.to_dict()

    @staticmethod
    def legacy_to_dto(legacy_dict: Dict[str, Any]) -> GraphDTO:
        return GraphDTO.model_validate(legacy_dict)

    @staticmethod
    def dto_to_legacy(dto: GraphDTO) -> Dict[str, Any]:
        return dto.model_dump()
