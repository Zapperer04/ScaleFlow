import re
from typing import List
from services.document_retrieval.candidate import Candidate
from services.answer_generation.answer_models import VerificationResult

class AnswerVerifier:
    def verify(self, answer_text: str, candidates: List[Candidate]) -> VerificationResult:
        if not answer_text:
            return VerificationResult(is_valid=False, verification_score=0.0)

        unsupported_claims = []
        contradictions = []
        missing_citations = []

        combined_context = " ".join([c.text.lower() for c in candidates])

        # 1. Check unsupported claims (simple heuristic: key terms in answer must be in context)
        # Find capitalized words (excluding first words)
        words = re.findall(r'\b[A-Z][a-z]+\b', answer_text)
        for word in words:
            if word.lower() not in combined_context:
                unsupported_claims.append(f"Claim about '{word}' is unsupported by context.")

        # 2. Check contradictions (heuristic: numbers in answer must be in context)
        numbers = re.findall(r'\b\d{3,}\b', answer_text)
        for num in numbers:
            if num not in combined_context:
                contradictions.append(f"Number contradiction: '{num}' is in answer but missing in context.")

        # 3. Check missing citations (sentences without [idx])
        sentences = re.split(r'(?<=[.!?])\s+', answer_text.strip())
        for idx, sentence in enumerate(sentences):
            if len(sentence) > 30 and not re.search(r'\[\d+\]', sentence):
                missing_citations.append(f"Sentence {idx+1} is missing citation support.")

        # Compute verification score
        violations = len(unsupported_claims) + len(contradictions) + len(missing_citations)
        score = max(1.0 - (violations * 0.15), 0.0)

        is_valid = (score >= 0.7) and (len(unsupported_claims) == 0) and (len(contradictions) == 0)

        return VerificationResult(
            is_valid=is_valid,
            unsupported_claims=unsupported_claims,
            contradictions=contradictions,
            missing_citations=missing_citations,
            verification_score=score
        )
