import re
from typing import List, Set, Dict, Any
from engine.document_retrieval.candidate import Candidate
from engine.answer_generation.answer_models import Citation

class CitationManager:
    def parse_citations(self, answer_text: str, candidates: List[Candidate]) -> List[Citation]:
        if not answer_text or not candidates:
            return []

        # Find all brackets like [1], [2], etc. in the text
        citations_found = re.findall(r'\[(\d+)\]', answer_text)
        unique_indices = sorted(list(set(int(idx) for idx in citations_found)))

        citations_list = []
        for index in unique_indices:
            # Match 1-indexed to candidate list
            candidate_idx = index - 1
            if 0 <= candidate_idx < len(candidates):
                cand = candidates[candidate_idx]
                
                citations_list.append(Citation(
                    index=index,
                    chunk_id=cand.chunk_id,
                    graph_node_ids=cand.graph_node_ids,
                    page_numbers=cand.page_numbers,
                    source_text=cand.text[:200] + "..." if len(cand.text) > 200 else cand.text,
                    metadata=cand.metadata
                ))

        return citations_list
