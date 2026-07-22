import math
from typing import List
from services.document_retrieval.experts.base_expert import BaseExpert
from services.document_retrieval.evidence import Evidence
from services.document_retrieval.query_understanding import QueryUnderstanding

class VectorExpert(BaseExpert):
    @property
    def name(self) -> str:
        return "vector"

    def retrieve(self, qu: QueryUnderstanding, doc_id: str, store) -> List[Evidence]:
        # Load embedding records from storage
        records = store.load_json(doc_id, "embeddings/vectors.json")
        if not records:
            return []

        query_vec = qu.embedding
        if not query_vec:
            return []

        evidence_list = []
        for rec in records:
            vector = rec.get("vector", [])
            if not vector or len(vector) != len(query_vec):
                continue

            # Compute Cosine Similarity
            dot_product = sum(a * b for a, b in zip(query_vec, vector))
            norm_a = math.sqrt(sum(a * a for a in query_vec))
            norm_b = math.sqrt(sum(b * b for b in vector))
            similarity = dot_product / (norm_a * norm_b) if norm_a * norm_b > 0 else 0.0

            if similarity > 0.3:  # Threshold limit
                evidence_list.append(Evidence(
                    id=f"ev-vec-{rec['chunk_id']}",
                    source=self.name,
                    evidence_type="chunk",
                    score=similarity,
                    confidence=0.85,
                    graph_node_ids=rec.get("graph_node_ids", []),
                    entity_ids=rec.get("entity_ids", []),
                    metadata={
                        "chunk_id": rec["chunk_id"],
                        "model": rec.get("embedding_model")
                    }
                ))

        # Sort by score descending
        evidence_list.sort(key=lambda x: x.score, reverse=True)
        return evidence_list[:15]
