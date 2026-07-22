from typing import Dict, Any
from services.document_pipeline.builders.base_builder import BaseBuilder
from services.document_pipeline.schemas import CanonicalDocument, MetadataRepresentation

class MetadataBuilder(BaseBuilder):
    @property
    def name(self) -> str:
        return "metadata"

    @property
    def version(self) -> str:
        return "1.0.0"

    def build(self, doc: CanonicalDocument, context: Dict[str, Any]) -> MetadataRepresentation:
        raw_meta = doc.metadata or {}
        
        title = raw_meta.get("title") or raw_meta.get("Title") or "Unknown Title"
        author = raw_meta.get("author") or raw_meta.get("Author") or "Unknown Author"
        language = raw_meta.get("language") or raw_meta.get("Language") or "en"
        doc_type = raw_meta.get("document_type") or raw_meta.get("DocumentType") or "PDF"
        creation_date = raw_meta.get("creation_date") or raw_meta.get("CreationDate") or ""
        page_count = len(doc.pages)

        # parser_version can be taken from parser metadata
        parser_version = doc.parser_metadata.get("parser_used", "1.0.0")

        return MetadataRepresentation(
            title=title,
            author=author,
            language=language,
            document_type=doc_type,
            creation_date=str(creation_date),
            page_count=page_count,
            parser_version=parser_version,
            graph_version="1.0.0",
            document_hash=doc.document_id
        )
