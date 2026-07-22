from typing import List, Dict, Any, Set
from engine.document_retrieval.candidate import Candidate

class ContextOptimizer:
    def optimize_context(self, candidates: List[Candidate], token_limit: int = 4000) -> List[Candidate]:
        if not candidates:
            return []

        # 1. Remove duplicate chunk IDs
        deduplicated: List[Candidate] = []
        seen_chunks = set()
        for c in candidates:
            if c.chunk_id not in seen_chunks:
                seen_chunks.add(c.chunk_id)
                deduplicated.append(c)

        # 2. Sort candidates to preserve document reading order
        # reading_order can be inferred from chunk_id suffix (e.g. chunk-0, chunk-1)
        def get_chunk_index(chunk_id: str) -> int:
            try:
                parts = chunk_id.split("-")
                return int(parts[-1])
            except Exception:
                return 9999

        deduplicated.sort(key=lambda x: get_chunk_index(x.chunk_id))

        # 3. Stitch adjacent chunks
        optimized: List[Candidate] = []
        for c in deduplicated:
            if not optimized:
                optimized.append(c)
            else:
                last = optimized[-1]
                last_idx = get_chunk_index(last.chunk_id)
                curr_idx = get_chunk_index(c.chunk_id)
                
                # If they are sequential and adjacent, stitch them!
                if curr_idx == last_idx + 1:
                    last.text += "\n" + c.text
                    last.chunk_id = f"{last.chunk_id}+{c.chunk_id}"
                    last.page_numbers = sorted(list(set(last.page_numbers + c.page_numbers)))
                    last.graph_node_ids = sorted(list(set(last.graph_node_ids + c.graph_node_ids)))
                    last.entities = sorted(list(set(last.entities + c.entities)))
                else:
                    optimized.append(c)

        # 4. Enforce Token / Word budget
        final_candidates: List[Candidate] = []
        total_words = 0
        word_limit = token_limit * 3 // 4  # Estimate words from tokens (1 token ~ 0.75 words)

        for c in optimized:
            word_count = len(c.text.split())
            if total_words + word_count <= word_limit:
                final_candidates.append(c)
                total_words += word_count
            else:
                # If chunk is too large but we still have budget, truncate it cleanly
                remaining_words = word_limit - total_words
                if remaining_words > 50:
                    truncated_text = " ".join(c.text.split()[:remaining_words]) + "..."
                    c.text = truncated_text
                    final_candidates.append(c)
                    total_words += remaining_words
                break

        return final_candidates
