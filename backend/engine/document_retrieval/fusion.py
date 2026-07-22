from typing import List, Dict, Any
from engine.document_retrieval.candidate import Candidate
from engine.document_retrieval.query_understanding import QueryUnderstanding

class FusionEngine:
    def fuse_candidates(self, candidates: List[Candidate], qu: QueryUnderstanding) -> List[Candidate]:
        if not candidates:
            return []

        # Group candidates by chunk_id
        grouped: Dict[str, List[Candidate]] = {}
        for c in candidates:
            grouped.setdefault(c.chunk_id, []).append(c)

        fused_candidates: List[Candidate] = []

        for chunk_id, group in grouped.items():
            # Find unique expert sources
            sources = set(c.source for c in group)
            agreement_count = len(sources)

            # Keep the primary candidate (one with highest score or confidence)
            primary = max(group, key=lambda x: x.score)

            # Compute normalized similarity (raw score)
            similarity = primary.score

            # Compute expert confidence breakdown
            confidence_breakdown = {c.source: c.confidence for c in group}
            avg_confidence = sum(confidence_breakdown.values()) / len(confidence_breakdown)

            # Best_for matching hints
            best_for_boost = 0.0
            chunk_best_for = primary.best_for or []
            
            if "table_lookup" in chunk_best_for and qu.table_probability > 0.6:
                best_for_boost += 0.25
            if "definition" in chunk_best_for and any(k in qu.query.lower() for k in ["define", "definition", "meaning"]):
                best_for_boost += 0.25
            if "entity" in chunk_best_for and len(qu.entities) > 1:
                best_for_boost += 0.2

            # Agreement boost
            agreement_boost = 0.0
            if agreement_count > 1:
                agreement_boost = (agreement_count - 1) * 0.15

            # Importance boost
            importance_boost = (primary.importance - 1.0) * 0.1 if primary.importance > 1.0 else 0.0

            # Calculate Final Score
            final_score = similarity + avg_confidence * 0.2 + best_for_boost + agreement_boost + importance_boost

            # Update primary candidate fields
            primary.score = round(final_score, 4)
            primary.confidence = round(avg_confidence, 4)
            primary.evidence.append(f"Fuesd from {agreement_count} experts. Agreement boost: {agreement_boost:.2f}")
            primary.metadata["confidence_breakdown"] = {
                "avg_confidence": avg_confidence,
                "sources": list(sources),
                "agreement_boost": agreement_boost,
                "best_for_boost": best_for_boost,
                "importance_boost": importance_boost,
                "breakdown": confidence_breakdown
            }

            fused_candidates.append(primary)

        # Sort by final score descending
        fused_candidates.sort(key=lambda x: x.score, reverse=True)
        return fused_candidates
