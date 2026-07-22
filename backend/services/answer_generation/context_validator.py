import re
from typing import List, Dict, Any, Set
from services.document_retrieval.candidate import Candidate

class ContextValidator:
    def validate_context(self, candidates: List[Candidate]) -> List[Candidate]:
        if not candidates:
            return []

        validated: List[Candidate] = []
        seen_texts: Set[str] = set()
        contradictory_warnings = []

        # 1. Clean duplicates & find contradictions
        for cand in candidates:
            clean_text = re.sub(r'\s+', ' ', cand.text.strip().lower())
            
            # Skip exact duplicates
            if clean_text in seen_texts:
                continue
            seen_texts.add(clean_text)

            # Heuristic contradiction checking (e.g. conflicting numbers associated with same keyword)
            for prev in validated:
                # If they share unique nouns but have different numbers
                shared_nouns = set(re.findall(r'\b[a-zA-Z]{4,}\b', cand.text.lower())).intersection(
                    set(re.findall(r'\b[a-zA-Z]{4,}\b', prev.text.lower()))
                )
                if len(shared_nouns) >= 1:
                    cand_nums = set(re.findall(r'\b\d{3,}\b', cand.text))
                    prev_nums = set(re.findall(r'\b\d{3,}\b', prev.text))
                    if cand_nums and prev_nums and not cand_nums.intersection(prev_nums):
                        contradictory_warnings.append(
                            f"Potential contradiction between {cand.chunk_id} and {prev.chunk_id} on numbers {cand_nums} vs {prev_nums}"
                        )

            validated.append(cand)

        # Log or record contradictory warnings inside candidate metadata
        if contradictory_warnings:
            for cand in validated:
                cand.metadata["contradictory_warnings"] = contradictory_warnings

        return validated
