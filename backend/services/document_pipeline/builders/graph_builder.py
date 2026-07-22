from typing import Dict, Any, List
from services.document_pipeline.builders.base_builder import BaseBuilder
from services.document_pipeline.schemas import CanonicalDocument, GraphNode, GraphEdge

class GraphBuilder(BaseBuilder):
    @property
    def name(self) -> str:
        return "graph"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def dependencies(self) -> List[str]:
        return ["metadata", "layout"]

    def build(self, doc: CanonicalDocument, context: Dict[str, Any]) -> Dict[str, Any]:
        # Validate and persist graph returned directly by the parser
        raw_graph = doc.graph or {"nodes": [], "edges": []}
        
        nodes = []
        for n in raw_graph.get("nodes", []):
            nodes.append(GraphNode(
                id=n.get("id"),
                type=n.get("type", "Paragraph"),
                text=n.get("text", ""),
                page=n.get("page", 1),
                bbox=n.get("bbox"),
                confidence=n.get("confidence", 1.0),
                metadata=n.get("metadata", {}),
                chunk_ids=n.get("chunk_ids", [])
            ))

        edges = []
        for e in raw_graph.get("edges", []):
            edges.append(GraphEdge(
                source=e.get("source"),
                target=e.get("target"),
                type=e.get("type", "contains"),
                metadata=e.get("metadata", {}),
                confidence=e.get("confidence", 1.0),
                builder=e.get("builder", "VLMParser")
            ))

        # Perform light verification / mapping
        node_ids = {n.id for n in nodes}
        # In case some edges reference non-existent nodes, filter them out to ensure consistency
        edges = [e for e in edges if e.source in node_ids and e.target in node_ids]

        # Populate a graph id map in the context for downstreams
        # Since VLM already computed the stable node IDs, the map is simple identity mapping
        graph_id_map = {n.id: n.id for n in nodes}
        # Map original layout block IDs to graph node IDs
        for block in doc.blocks:
            if block.id in node_ids:
                graph_id_map[block.id] = block.id
            else:
                # Find matching node by text or index if not direct
                for n in nodes:
                    if n.text == block.text:
                        graph_id_map[block.id] = n.id
                        break
        context["graph_id_map"] = graph_id_map

        return {
            "nodes": [n.__dict__ for n in nodes],
            "edges": [e.__dict__ for e in edges]
        }
