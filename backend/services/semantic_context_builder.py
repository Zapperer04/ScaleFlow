import json
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

class SemanticContextBuilder:
    def build(self, query_type: str, reranked_chunks: List[Dict]) -> str:
        """
        Builds and serializes context based on query intent and retrieved semantic graph metadata.
        """
        if not reranked_chunks:
            return ""

        query_type = str(query_type).upper()

        if "ENTITY" in query_type or "LOOKUP" in query_type:
            return self.serialize_entities(reranked_chunks)
        elif "ATTRIBUTE" in query_type:
            return self.serialize_attributes(reranked_chunks)
        elif "RELATION" in query_type:
            return self.serialize_relationships(reranked_chunks)
        elif "SUMMARY" in query_type:
            return self.serialize_summary(reranked_chunks)
        elif "REASON" in query_type:
            return self.serialize_reasoning(reranked_chunks)
        elif "AGGREGAT" in query_type:
            return self.serialize_aggregation(reranked_chunks)
        
        # Default: Fallback to structured hybrid context
        return self.serialize_entities(reranked_chunks)

    def serialize_entities(self, chunks: List[Dict]) -> str:
        # Group by entity_group
        groups = {}
        for c in chunks:
            eg = c.get("entity_group") or "unknown"
            if eg not in groups:
                groups[eg] = []
            groups[eg].append(c)

        serialized = []
        for eg, nodes in groups.items():
            if eg == "unknown" or eg == "":
                # Fallback to plain source formatting for un-grouped elements
                for n in nodes:
                    serialized.append(f"[Source {n.get('chunk_id')} (Category: {n.get('semantic_category', 'unknown')}):\n{n.get('chunk_text', '')}\n")
                continue

            serialized.append(f"Entity Group: {eg}")
            cat = nodes[0].get("semantic_category") or "unknown"
            serialized.append(f"Category: {cat}")
            serialized.append("Attributes:")
            for n in nodes:
                text = n.get("chunk_text") or n.get("text") or ""
                # Strip leading metadata numbers like (71) or 1)
                clean_text = text.strip()
                serialized.append(f"- {clean_text}")
            serialized.append("")
        return "\n".join(serialized)

    def serialize_attributes(self, chunks: List[Dict]) -> str:
        serialized = []
        for c in chunks:
            text = (c.get("chunk_text") or c.get("text") or "").strip()
            cat = c.get("semantic_category") or "unknown"
            serialized.append(f"Category: {cat}")
            serialized.append(f"Attributes:\n- {text}\n")
        return "\n".join(serialized)

    def serialize_relationships(self, chunks: List[Dict]) -> str:
        serialized = []
        for c in chunks:
            node_id = c.get("chunk_id") or "unknown"
            text = (c.get("chunk_text") or c.get("text") or "").strip()
            neighbors = c.get("neighbors") or []
            serialized.append(f"Entity Node: {node_id}")
            serialized.append(f"Content: {text}")
            if neighbors:
                serialized.append("Relationships:")
                for n in neighbors:
                    serialized.append(f"- connected_to -> {n}")
            serialized.append("")
        return "\n".join(serialized)

    def serialize_summary(self, chunks: List[Dict]) -> str:
        serialized = []
        for idx, c in enumerate(chunks):
            text = c.get("chunk_text") or c.get("text") or ""
            serialized.append(f"[Source {idx+1}]: {text}")
        return "\n".join(serialized)

    def serialize_reasoning(self, chunks: List[Dict]) -> str:
        # JSON graph representation
        graph_nodes = []
        for c in chunks:
            graph_nodes.append({
                "node_id": c.get("chunk_id") or c.get("node_id"),
                "semantic_category": c.get("semantic_category") or "unknown",
                "entity_group": c.get("entity_group") or "unknown",
                "text": c.get("chunk_text") or c.get("text") or "",
                "relationships": c.get("neighbors") or []
            })
        return json.dumps({"graph_nodes": graph_nodes}, indent=2)

    def serialize_aggregation(self, chunks: List[Dict]) -> str:
        # Hierarchical entity tree
        groups = {}
        for c in chunks:
            eg = c.get("entity_group") or "unknown"
            if eg not in groups:
                groups[eg] = []
            groups[eg].append(c)

        serialized = []
        for eg, nodes in groups.items():
            serialized.append(f"Entity: {eg}")
            for idx, n in enumerate(nodes):
                text = (n.get("chunk_text") or n.get("text") or "").strip()
                cat = n.get("semantic_category") or "unknown"
                connector = " ├─" if idx < len(nodes) - 1 else " └─"
                serialized.append(f"{connector} [{cat}]: {text}")
            serialized.append("")
        return "\n".join(serialized)
