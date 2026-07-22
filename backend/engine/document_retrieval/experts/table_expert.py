from typing import List
from engine.document_retrieval.experts.base_expert import BaseExpert
from engine.document_retrieval.evidence import Evidence
from engine.document_retrieval.query_understanding import QueryUnderstanding

class TableExpert(BaseExpert):
    @property
    def name(self) -> str:
        return "table"

    def retrieve(self, qu: QueryUnderstanding, doc_id: str, store) -> List[Evidence]:
        tables = store.load_json(doc_id, "tables/tables.json")
        if not tables:
            return []

        evidence_list = []
        for table in tables:
            t_caption = table.get("caption") or ""
            t_headers = table.get("headers") or []
            t_id = table.get("id")

            # Check matches
            score = 0.0
            matched_reason = []

            # 1. Caption matches
            caption_matches = sum(1 for kw in qu.keywords if kw in t_caption.lower())
            if caption_matches > 0:
                score += (float(caption_matches) / len(qu.keywords)) * 0.8
                matched_reason.append("caption matched query keywords")

            # 2. Header matches
            header_matches = 0
            for h in t_headers:
                if any(kw in h.lower() for kw in qu.keywords):
                    header_matches += 1
            if header_matches > 0:
                score += (float(header_matches) / len(t_headers)) * 0.5
                matched_reason.append("table headers matched query keywords")

            # 3. Explicit Table query intent
            if qu.table_probability > 0.6:
                score += 0.2
                matched_reason.append("high table query probability")

            if score > 0.2:
                evidence_list.append(Evidence(
                    id=f"ev-table-{t_id}",
                    source=self.name,
                    evidence_type="table",
                    score=min(score, 1.0),
                    confidence=qu.table_probability,
                    table_ids=[t_id],
                    graph_node_ids=[table.get("graph_node_id")] if table.get("graph_node_id") else [],
                    metadata={
                        "caption": t_caption,
                        "headers": t_headers,
                        "matched_reason": matched_reason
                    }
                ))

        # Sort by score descending
        evidence_list.sort(key=lambda x: x.score, reverse=True)
        return evidence_list
