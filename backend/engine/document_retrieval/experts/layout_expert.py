from typing import List
from engine.document_retrieval.experts.base_expert import BaseExpert
from engine.document_retrieval.evidence import Evidence
from engine.document_retrieval.query_understanding import QueryUnderstanding

class LayoutExpert(BaseExpert):
    @property
    def name(self) -> str:
        return "layout"

    def retrieve(self, qu: QueryUnderstanding, doc_id: str, store) -> List[Evidence]:
        layout = store.load_json(doc_id, "layout/layout.json")
        if not layout:
            return []

        visual_blocks = layout.get("visual_blocks", {})
        if not visual_blocks:
            return []

        spatial_constraints = qu.spatial_constraints
        if not spatial_constraints:
            return []

        evidence_list = []
        for block_id, block in visual_blocks.items():
            bbox = block.get("bbox", {})
            ymin = bbox.get("ymin", 0.0)
            xmin = bbox.get("xmin", 0.0)
            ymax = bbox.get("ymax", 1.0)
            xmax = bbox.get("xmax", 1.0)

            score = 0.0
            matched_reason = []

            # Match spatial criteria
            for constraint in spatial_constraints:
                if constraint == "top" and ymin < 0.25:
                    score += 0.4
                    matched_reason.append("positioned in top region")
                elif constraint == "bottom" and ymax > 0.75:
                    score += 0.4
                    matched_reason.append("positioned in bottom region")
                elif constraint == "left" and xmin < 0.25:
                    score += 0.4
                    matched_reason.append("positioned in left region")
                elif constraint == "right" and xmax > 0.75:
                    score += 0.4
                    matched_reason.append("positioned in right region")

            # Keyword matching on font style if style metadata matches
            if score > 0.0:
                evidence_list.append(Evidence(
                    id=f"ev-layout-{block_id}",
                    source=self.name,
                    evidence_type="block",
                    score=score,
                    confidence=0.7,
                    layout_ids=[block_id],
                    metadata={
                        "page": block.get("page"),
                        "type": block.get("type"),
                        "matched_reason": matched_reason
                    }
                ))

        # Sort and limit
        evidence_list.sort(key=lambda x: x.score, reverse=True)
        return evidence_list[:10]
