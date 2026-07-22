from typing import List, Dict, Any, Set
from engine.document_retrieval.experts.base_expert import BaseExpert
from engine.document_retrieval.evidence import Evidence
from engine.document_retrieval.query_understanding import QueryUnderstanding

class EntityExpert(BaseExpert):
    @property
    def name(self) -> str:
        return "entity"

    def retrieve(self, qu: QueryUnderstanding, doc_id: str, store) -> List[Evidence]:
        raw_entities = store.load_json(doc_id, "entities/entities.json")
        if not raw_entities:
            return []

        entities_list = raw_entities.get("entities", [])
        edges_list = raw_entities.get("edges", [])

        # Find matching entities by name, normalized value, or aliases
        matched_records = []
        matched_names: Set[str] = set()

        for ent in entities_list:
            e_name = ent.get("name", "")
            e_norm = ent.get("normalized_value", "")
            e_aliases = ent.get("aliases", [])

            # Match criteria
            matched = False
            # Check explicit query entities
            for q_ent in qu.entities:
                if q_ent.lower() == e_name.lower() or q_ent.lower() == e_norm.lower() or any(q_ent.lower() == al.lower() for al in e_aliases):
                    matched = True
                    break
            
            # Check keywords matching
            if not matched:
                for kw in qu.keywords:
                    if kw in e_name.lower() or kw in e_norm.lower() or any(kw in al.lower() for al in e_aliases):
                        matched = True
                        break

            if matched:
                matched_records.append(ent)
                matched_names.add(ent["id"])

        if not matched_records:
            return []

        # Find co-occurring entities (neighbors in entity graph)
        co_occurring: Set[str] = set()
        for edge in edges_list:
            src = edge.get("source")
            tgt = edge.get("target")
            e_type = edge.get("type")
            
            if src in matched_names and e_type == "mentioned_with":
                co_occurring.add(tgt)
            elif tgt in matched_names and e_type == "mentioned_with":
                co_occurring.add(src)

        # Build Evidence
        evidence_list = []
        for ent in matched_records:
            evidence_list.append(Evidence(
                id=f"ev-entity-{ent['id']}",
                source=self.name,
                evidence_type="entity",
                score=1.0,
                confidence=0.9,
                entity_ids=[ent["id"]] + list(co_occurring),
                graph_node_ids=ent.get("graph_node_ids", []),
                metadata={
                    "name": ent["name"],
                    "type": ent["type"],
                    "aliases": ent.get("aliases", [])
                }
            ))

        return evidence_list
