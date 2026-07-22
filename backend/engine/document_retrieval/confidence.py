from typing import Dict, List
from engine.document_retrieval.evidence import Evidence

class ConfidenceCalibrator:
    def calibrate(self, evidence: List[Evidence]) -> Dict[str, float]:
        if not evidence:
            return {"vector": 0.0, "graph": 0.0, "entity": 0.0}

        confidences = {"vector": 0.0, "graph": 0.0, "entity": 0.0, "table": 0.0, "layout": 0.0}
        counts = {"vector": 0, "graph": 0, "entity": 0, "table": 0, "layout": 0}

        for ev in evidence:
            src = ev.source
            if src in confidences:
                confidences[src] += ev.confidence
                counts[src] += 1

        # Calculate average confidence per source
        return {
            src: (confidences[src] / counts[src] if counts[src] > 0 else 0.0)
            for src in confidences
        }
