from typing import List, Dict, Any, Set
from services.document_retrieval.evidence import Evidence
from services.document_retrieval.candidate import Candidate

class CandidateBuilder:
    def build_candidates(self, evidence_list: List[Evidence], doc_id: str, store) -> List[Candidate]:
        if not evidence_list:
            return []

        # Load chunks from storage
        chunks_raw = store.load_json(doc_id, "chunks/chunks.json")
        if not chunks_raw:
            return []

        # Load layout blocks mapping
        layout = store.load_json(doc_id, "layout/layout.json") or {}
        visual_blocks = layout.get("visual_blocks", {})

        # Map graph node ID -> list of chunk dicts
        node_to_chunks: Dict[str, List[Dict[str, Any]]] = {}
        # Map table ID -> list of chunk dicts
        table_to_chunks: Dict[str, List[Dict[str, Any]]] = {}
        # Map chunk_id -> chunk dict
        chunk_map: Dict[str, Dict[str, Any]] = {}

        for chunk in chunks_raw:
            c_id = chunk.get("chunk_id")
            chunk_map[c_id] = chunk
            
            # Map node IDs
            for node_id in chunk.get("graph_node_ids", []):
                node_to_chunks.setdefault(node_id, []).append(chunk)

            # Map table refs
            for table_ref in chunk.get("table_refs", []):
                table_to_chunks.setdefault(table_ref, []).append(chunk)

        candidates: List[Candidate] = []
        assembled_chunks: Set[str] = set()

        for idx, ev in enumerate(evidence_list):
            matched_chunks: List[Dict[str, Any]] = []

            # 1. Direct chunk ID reference from vector evidence
            direct_id = ev.metadata.get("chunk_id")
            if direct_id and direct_id in chunk_map:
                matched_chunks.append(chunk_map[direct_id])

            # 2. Match via graph node IDs
            for n_id in ev.graph_node_ids:
                if n_id in node_to_chunks:
                    matched_chunks.extend(node_to_chunks[n_id])

            # 3. Match via layout block IDs
            for l_id in ev.layout_ids:
                # Find which graph node/chunk matches this visual block text or ID
                if l_id in node_to_chunks:
                    matched_chunks.extend(node_to_chunks[l_id])

            # 4. Match via table IDs
            for t_id in ev.table_ids:
                if t_id in table_to_chunks:
                    matched_chunks.extend(table_to_chunks[t_id])

            # Deduplicate matched chunks within this evidence object
            unique_chunks = []
            seen_ids = set()
            for chunk in matched_chunks:
                c_id = chunk["chunk_id"]
                if c_id not in seen_ids:
                    seen_ids.add(c_id)
                    unique_chunks.append(chunk)

            # Build Candidates
            for chunk in unique_chunks:
                c_id = chunk["chunk_id"]
                
                # Check if already assembled to avoid duplication
                # We can assemble the same chunk from different evidence objects,
                # but we'll record multiple evidence sources in the candidate!
                candidate_id = f"cand-{c_id}"
                
                # Retrieve visual bounding box if available
                bbox = chunk.get("bbox")
                
                cand = Candidate(
                    id=candidate_id,
                    chunk_id=c_id,
                    source=ev.source,
                    text=chunk.get("text", ""),
                    score=ev.score,
                    confidence=ev.confidence,
                    retrieval_rank=idx + 1,
                    graph_distance=ev.metadata.get("graph_distance"),
                    entities=chunk.get("entities", []),
                    page_numbers=chunk.get("page_range", []),
                    graph_node_ids=chunk.get("graph_node_ids", []),
                    bbox=bbox,
                    best_for=chunk.get("best_for", []),
                    importance=chunk.get("importance_score", 1.0),
                    section_path=chunk.get("section_path", []),
                    evidence=[f"Retrieved by {ev.source} expert: {ev.metadata.get('matched_reason', ['matched text'])[0]}"],
                    metadata={
                        "expert_source": ev.source,
                        "raw_score": ev.score,
                        "raw_confidence": ev.confidence
                    }
                )
                candidates.append(cand)

        return candidates
