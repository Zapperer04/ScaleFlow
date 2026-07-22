import re
from typing import List, Dict
from services.document_retrieval.candidate import Candidate
from services.answer_generation.answer_models import VerificationResult, AnswerConfidence

class ConfidenceEngine:
    def calculate_confidence(
        self,
        retrieval_confidence: float,
        verification: VerificationResult,
        candidates: List[Candidate],
        answer_text: str
    ) -> AnswerConfidence:
        # 1. Generation confidence: derived from candidate scores
        avg_candidate_score = sum(c.score for c in candidates) / len(candidates) if candidates else 0.5
        generation_confidence = min(max(avg_candidate_score, 0.0), 1.0)

        # 2. Citation coverage: ratio of sentences containing citations
        sentences = [s for s in re.split(r'(?<=[.!?])\s+', answer_text.strip()) if len(s.strip()) > 15]
        cited_sentences = sum(1 for s in sentences if re.search(r'\[\d+\]', s))
        citation_coverage = cited_sentences / len(sentences) if sentences else 0.0

        # 3. Evidence agreement
        # Boost confidence if multiple candidates agree or if the candidate score is high
        unique_sources = set(c.source for c in candidates)
        agreement_factor = min(len(unique_sources) / 3.0, 1.0)

        # 4. Verification score
        verification_score = verification.verification_score

        # Combine Overall Confidence Score
        overall_score = (
            retrieval_confidence * 0.25 +
            generation_confidence * 0.25 +
            citation_coverage * 0.2 +
            verification_score * 0.2 +
            agreement_factor * 0.1
        )

        overall_score = round(min(max(overall_score, 0.0), 1.0), 4)

        return AnswerConfidence(
            overall_score=overall_score,
            retrieval_confidence=retrieval_confidence,
            generation_confidence=generation_confidence,
            citation_coverage=citation_coverage,
            verification_score=verification_score,
            confidence_breakdown={
                "retrieval": retrieval_confidence,
                "generation": generation_confidence,
                "citation_coverage": citation_coverage,
                "verification": verification_score,
                "agreement_factor": agreement_factor
            }
        )
