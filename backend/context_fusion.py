from typing import List, Dict, Any, Optional

class FusedContext:
    def __init__(self):
        self.sections: List[Dict[str, Any]] = []
        self.tables: List[Dict[str, Any]] = []
        self.figures: List[Dict[str, Any]] = []
        self.captions: List[Dict[str, Any]] = []
        self.references: List[Dict[str, Any]] = []
        self.graph_evidence: List[Dict[str, Any]] = []
        self.supporting_chunks: List[Dict[str, Any]] = []
        # Mapping to track where each evidence came from
        self.provenance_map: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sections": self.sections,
            "tables": self.tables,
            "figures": self.figures,
            "captions": self.captions,
            "references": self.references,
            "graph_evidence": self.graph_evidence,
            "supporting_chunks": self.supporting_chunks
        }

    def to_prompt_string(self, token_limit: int = 4000) -> str:
        lines = []
        
        sections_str = "\n".join(f"- Section {s.get('section_id')}: {s.get('text')}" for s in self.sections)
        tables_str = "\n".join(f"- Table {t.get('chunk_id')}: {t.get('text')}" for t in self.tables)
        figures_str = "\n".join(f"- Figure {f.get('chunk_id')}: {f.get('text')}" for f in self.figures)
        captions_str = "\n".join(f"- Caption {c.get('chunk_id')}: {c.get('text')}" for c in self.captions)
        references_str = "\n".join(f"- Reference {r.get('chunk_id')}: {r.get('text')}" for r in self.references)
        graph_str = "\n".join(f"- Graph Node {g.get('id')}: {g.get('text')}" for g in self.graph_evidence)
        chunks_str = "\n".join(f"- Chunk {sc.get('chunk_id')}: {sc.get('text')}" for sc in self.supporting_chunks)

        if sections_str:
            lines.append(f"=== SECTIONS ===\n{sections_str}")
        if tables_str:
            lines.append(f"=== TABLES ===\n{tables_str}")
        if figures_str:
            lines.append(f"=== FIGURES ===\n{figures_str}")
        if captions_str:
            lines.append(f"=== CAPTIONS ===\n{captions_str}")
        if references_str:
            lines.append(f"=== REFERENCES ===\n{references_str}")
        if graph_str:
            lines.append(f"=== GRAPH EVIDENCE ===\n{graph_str}")
        if chunks_str:
            lines.append(f"=== SUPPORTING EVIDENCE ===\n{chunks_str}")

        full_context = "\n\n".join(lines)
        
        # Simple token limit enforcement (words fallback)
        words = full_context.split()
        if len(words) > token_limit:
            return " ".join(words[:token_limit]) + "\n... [TRUNCATED DUE TO BUDGET]"
        return full_context

class ContextFusion:
    def __init__(self, token_budget: int = 4000):
        self.token_budget = token_budget

    def fuse_context(self, reranked_candidates: List[Dict[str, Any]], graph_nodes: Optional[List[Dict[str, Any]]] = None) -> FusedContext:
        fused = FusedContext()
        seen_chunks = set()
        seen_nodes = set()

        # 1. Process candidate chunks
        for cand in reranked_candidates:
            cid = cand["chunk_id"]
            if cid in seen_chunks:
                continue
            seen_chunks.add(cid)
            
            chunk_data = cand.get("chunk") or {}
            text = cand.get("text", "")
            
            # Map chunk to its structural categories
            # Metadata or chunk type mapping
            chunk_type = chunk_data.get("metadata", {}).get("type", "").lower() or chunk_data.get("content_type", "").lower()
            
            evidence_item = {
                "chunk_id": cid,
                "text": text,
                "page": cand.get("page") or chunk_data.get("page"),
                "bbox": cand.get("bbox") or chunk_data.get("bbox"),
                "section_id": cand.get("section_id") or chunk_data.get("section_id") or chunk_data.get("section"),
                "graph_node_ids": chunk_data.get("graph_node_ids", [])
            }
            
            fused.provenance_map[cid] = evidence_item

            if "table" in chunk_type:
                fused.tables.append(evidence_item)
            elif "figure" in chunk_type:
                fused.figures.append(evidence_item)
            elif "caption" in chunk_type:
                fused.captions.append(evidence_item)
            elif "reference" in chunk_type:
                fused.references.append(evidence_item)
            elif "section" in chunk_type:
                fused.sections.append(evidence_item)
            else:
                fused.supporting_chunks.append(evidence_item)

        # 2. Process additional Graph Evidence
        if graph_nodes:
            for node in graph_nodes:
                nid = node.get("id")
                if nid in seen_nodes:
                    continue
                seen_nodes.add(nid)
                
                # Check if this node is already covered by a chunk
                covered = False
                for cid, item in fused.provenance_map.items():
                    if nid in item.get("graph_node_ids", []):
                        covered = True
                        break
                
                if not covered:
                    evidence_item = {
                        "id": nid,
                        "text": node.get("text", ""),
                        "page": node.get("page"),
                        "bbox": node.get("bbox"),
                        "type": node.get("type", "")
                    }
                    fused.graph_evidence.append(evidence_item)
                    fused.provenance_map[nid] = evidence_item

        return fused
