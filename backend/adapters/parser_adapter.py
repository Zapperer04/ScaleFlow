from typing import Dict, Any
from backend.domain.aggregates.document import Document
from backend.domain.value_objects.document_id import DocumentId
from backend.dto.parsing import ParserResponseDTO

class ParserAdapter:
    @staticmethod
    def legacy_to_domain(legacy_report: Any, filename: str, doc_id: int) -> Document:
        # PreprocessingReport or dict
        if hasattr(legacy_report, "to_dict"):
            data = legacy_report.to_dict()
        elif hasattr(legacy_report, "__dict__"):
            data = legacy_report.__dict__
        else:
            data = dict(legacy_report)

        return Document(
            document_id=DocumentId(doc_id),
            filename=filename,
            pages=[],
            chunks=[],
            graph=None,
            metadata=data,
            artifacts=[],
        )

    @staticmethod
    def domain_to_legacy(domain_doc: Document) -> Dict[str, Any]:
        return domain_doc.metadata

    @staticmethod
    def legacy_to_dto(legacy_report: Any) -> ParserResponseDTO:
        if hasattr(legacy_report, "__dict__"):
            data = legacy_report.__dict__
        else:
            data = dict(legacy_report)
        return ParserResponseDTO(
            document_type=data.get("document_type", "DIGITAL"),
            pages=data.get("pages", []),
            metadata=data,
            timings=data.get("timings", {}),
        )

    @staticmethod
    def dto_to_legacy(dto: ParserResponseDTO) -> Dict[str, Any]:
        return dto.metadata
