import math
from typing import List, Dict, Any, Set
from engine.document_retrieval.experts.base_expert import BaseExpert
from engine.document_retrieval.evidence import Evidence
from engine.document_retrieval.query_understanding import QueryUnderstanding

class GraphExpert(BaseExpert):
    @property
    def name(self) -> str:
        return "graph"

    def retrieve(self, qu: QueryUnderstanding, doc_id: str, store) -> List[Evidence]:
        # 1. Load graph nodes and edges
        nodes = store.load_json(doc_id, "graph/nodes.json")
        edges = store.load_json(doc_id, "graph/edges.json")
        if not nodes or not edges:
            return []

        # Map node ID -> node dict
        node_map = {n["id"]: n for n in nodes}

        # 2. Match seed nodes using Heading embeddings from vectors.json
        embeddings = store.load_json(doc_id, "embeddings/vectors.json") or []
        heading_scores: Dict[str, float] = {}

        query_vec = qu.embedding
        if query_vec:
            for emb in embeddings:
                # Find heading elements
                if emb.get("metadata", {}).get("type") == "heading":
                    vector = emb.get("vector", [])
                    if len(vector) == len(query_vec):
                        dot_product = sum(a * b for a, b in zip(query_vec, vector))
                        norm_a = math.sqrt(sum(a * a for a in query_vec))
                        norm_b = math.sqrt(sum(b * b for b in vector))
                        similarity = dot_product / (norm_a * norm_b) if norm_a * norm_b > 0 else 0.0
                        
                        target_id = emb.get("chunk_id")
                        if target_id:
                            heading_scores[target_id] = similarity

        # Also fallback to keyword matching for seed detection
        for n_id, node in node_map.items():
            if node["type"] in ["Heading", "Section"]:
                kw_matches = sum(1 for kw in qu.keywords if kw in node["text"].lower())
                if kw_matches > 0:
                    score = float(kw_matches) / len(qu.keywords)
                    heading_scores[n_id] = max(heading_scores.get(n_id, 0.0), score)

        # Sort seed nodes
        seeds = [n_id for n_id, score in heading_scores.items() if score > 0.1]
        seeds.sort(key=lambda x: heading_scores[x], reverse=True)
        seeds = seeds[:5]  # Top seeds

        if not seeds:
            return []

        # 3. Perform graph traversal (1-hop neighbors)
        traversed: Set[str] = set(seeds)
        edge_evidence: List[str] = []

        for edge in edges:
            src = edge.get("source")
            tgt = edge.get("target")
            e_type = edge.get("type")
            
            if src in seeds:
                traversed.add(tgt)
                edge_evidence.append(f"traversed: {src} -> {e_type} -> {tgt}")
            elif tgt in seeds:
                traversed.add(src)
                edge_evidence.append(f"traversed: {tgt} <- {e_type} <- {src}")

        # Return Evidence listing all traversed node IDs
        evidence_list = []
        for n_id in traversed:
            node = node_map.get(n_id)
            if not node:
                continue

            # Graph distance (0 for seeds, 1 for neighbors)
            dist = 0 if n_id in seeds else 1
            score = heading_scores.get(n_id, 0.8 if dist == 0 else 0.5)

            evidence_list.append(Evidence(
                id=f"ev-graph-{n_id}",
                source=self.name,
                evidence_type="node",
                score=score,
                confidence=qu.graph_probability,
                graph_node_ids=[n_id],
                metadata={
                    "node_type": node["type"],
                    "text": node["text"][:100],
                    "graph_distance": dist,
                    "edge_path": edge_evidence[:3]
                }
            ))

        return evidence_list
