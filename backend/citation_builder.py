import re
from typing import List, Dict, Any, Optional
from context_fusion import FusedContext

class CitationBuilder:
    def __init__(self):
        pass

    def build_citations(self, answer_text: str, fused_context: FusedContext) -> List[Dict[str, Any]]:
        citations = []
        resolved_indices = set()
        
        # 1. Look for explicit bracketed chunk citations, e.g., [chunk_doc_1], [chunk_12]
        matches = re.finditer(r"\[(chunk_[^\]\s]+)\]", answer_text)
        for idx, match in enumerate(matches):
            chunk_id = match.group(1)
            # Resolve against fused context chunk map
            item = fused_context.provenance_map.get(chunk_id)
            if item and chunk_id not in resolved_indices:
                resolved_indices.add(chunk_id)
                
                # Bounding box extraction
                bbox = item.get("bbox")
                if bbox and isinstance(bbox, dict) and "y1" in bbox:
                    bbox = {"ymin": bbox.get("y1"), "xmin": bbox.get("x1"), "ymax": bbox.get("y2"), "xmax": bbox.get("x2")}

                gn_ids = item.get("graph_node_ids", [])
                node_id = gn_ids[0] if gn_ids else (item.get("id") or "")
                
                citations.append({
                    "citation_id": f"cit_{idx + 1}",
                    "page": item.get("page", 1),
                    "bbox": bbox or {"ymin": 0.0, "xmin": 0.0, "ymax": 1.0, "xmax": 1.0},
                    "section": item.get("section_id") or "unknown",
                    "chunk_id": chunk_id,
                    "graph_node_id": node_id,
                    "snippet": item.get("text", "")[:200]
                })

        # 2. Look for numbered citation markers like [1], [2], which correspond to list position
        # We can map these to the ordered list of supporting chunks, tables, figures
        numbered_matches = re.finditer(r"\[(\d+)\]", answer_text)
        all_ordered_items = (
            fused_context.sections + 
            fused_context.tables + 
            fused_context.figures + 
            fused_context.captions + 
            fused_context.references + 
            fused_context.graph_evidence + 
            fused_context.supporting_chunks
        )
        
        for idx, match in enumerate(numbered_matches):
            num = int(match.group(1))
            # 1-indexed mapping
            if 0 < num <= len(all_ordered_items):
                item = all_ordered_items[num - 1]
                chunk_id = item.get("chunk_id") or item.get("id") or f"item_{num}"
                if chunk_id not in resolved_indices:
                    resolved_indices.add(chunk_id)
                    
                    bbox = item.get("bbox")
                    if bbox and isinstance(bbox, dict) and "y1" in bbox:
                        bbox = {"ymin": bbox.get("y1"), "xmin": bbox.get("x1"), "ymax": bbox.get("y2"), "xmax": bbox.get("x2")}
                        
                    gn_ids = item.get("graph_node_ids", [])
                    node_id = gn_ids[0] if gn_ids else (item.get("id") or "")
                    
                    citations.append({
                        "citation_id": f"cit_num_{num}",
                        "page": item.get("page", 1),
                        "bbox": bbox or {"ymin": 0.0, "xmin": 0.0, "ymax": 1.0, "xmax": 1.0},
                        "section": item.get("section_id") or "unknown",
                        "chunk_id": chunk_id,
                        "graph_node_id": node_id,
                        "snippet": item.get("text", "")[:200]
                    })

        # 3. Fallback: sentence fuzzy match
        # Split answer into sentences and search for high-overlap snippets in context
        if not citations:
            sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', answer_text)
            cit_idx = 1
            for sent in sentences:
                sent = sent.strip()
                if len(sent) < 30:
                    continue
                # Try finding a chunk containing similar words
                sent_words = set(sent.lower().split())
                best_match = None
                best_overlap = 0
                
                for item in all_ordered_items:
                    item_text = item.get("text", "").lower()
                    overlap = sum(1 for w in sent_words if w in item_text and len(w) > 3)
                    if overlap > best_overlap:
                        best_overlap = overlap
                        best_match = item
                        
                if best_match and best_overlap > 5: # significant overlap threshold
                    chunk_id = best_match.get("chunk_id") or best_match.get("id")
                    if chunk_id not in resolved_indices:
                        resolved_indices.add(chunk_id)
                        
                        bbox = best_match.get("bbox")
                        if bbox and isinstance(bbox, dict) and "y1" in bbox:
                            bbox = {"ymin": bbox.get("y1"), "xmin": bbox.get("x1"), "ymax": bbox.get("y2"), "xmax": bbox.get("x2")}
                            
                        gn_ids = best_match.get("graph_node_ids", [])
                        node_id = gn_ids[0] if gn_ids else (best_match.get("id") or "")
                        
                        citations.append({
                            "citation_id": f"cit_fuzzy_{cit_idx}",
                            "page": best_match.get("page", 1),
                            "bbox": bbox or {"ymin": 0.0, "xmin": 0.0, "ymax": 1.0, "xmax": 1.0},
                            "section": best_match.get("section_id") or "unknown",
                            "chunk_id": chunk_id,
                            "graph_node_id": node_id,
                            "snippet": best_match.get("text", "")[:200]
                        })
                        cit_idx += 1

        return citations
