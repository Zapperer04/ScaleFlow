import hashlib
from typing import Dict, Any, List
from services.document_pipeline.builders.base_builder import BaseBuilder
from services.document_pipeline.schemas import (
    CanonicalDocument,
    EntityGraph,
    EntityRecord,
    EntityEdge
)

class EntityBuilder(BaseBuilder):
    @property
    def name(self) -> str:
        return "entities"

    @property
    def version(self) -> str:
        return "1.0.0"

    def build(self, doc: CanonicalDocument, context: Dict[str, Any]) -> EntityGraph:
        entities_list: List[EntityRecord] = []
        edges_list: List[EntityEdge] = []

        # Validate and persist entities returned directly by the VLM parser
        for idx, ent in enumerate(doc.entities):
            # Generate deterministic stable ID based on name and type
            hasher = hashlib.sha256()
            hasher.update(f"{doc.document_id}-{ent.name.lower()}-{ent.type.lower()}".encode())
            ent_id = f"ent-{hasher.hexdigest()[:16]}"

            rec = EntityRecord(
                id=ent_id,
                name=ent.name,
                type=ent.type,
                normalized_value=ent.normalized_value,
                aliases=ent.aliases,
                occurrences=ent.occurrences
            )
            entities_list.append(rec)

            # Map occurrences (appears_in edges)
            for occ in ent.occurrences:
                block_id = occ.get("block_id")
                if block_id:
                    edges_list.append(EntityEdge(
                        source=ent_id,
                        target=block_id,
                        type="appears_in",
                        metadata={"page": occ.get("page")}
                    ))

        return EntityGraph(entities=entities_list, edges=edges_list)
