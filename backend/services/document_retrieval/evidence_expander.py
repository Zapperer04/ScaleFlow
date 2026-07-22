from typing import List, Dict, Any, Set
from services.document_retrieval.evidence import Evidence

class EvidenceExpander:
    def expand(self, evidence_list: List[Evidence], doc_id: str, store) -> List[Evidence]:
        if not evidence_list:
            return []

        # Load graph to perform traversal expansion
        nodes = store.load_json(doc_id, "graph/nodes.json")
        edges = store.load_json(doc_id, "graph/edges.json")
        if not nodes or not edges:
            return evidence_list  # Return unexpanded if graph is missing

        # Map node ID -> connected node relationships
        graph_connections: Dict[str, List[Dict[str, Any]]] = {}
        for edge in edges:
            src = edge.get("source")
            tgt = edge.get("target")
            e_type = edge.get("type")
            if src and tgt:
                graph_connections.setdefault(src, []).append({"target": tgt, "type": e_type, "direction": "forward"})
                graph_connections.setdefault(tgt, []).append({"target": src, "type": e_type, "direction": "backward"})

        expanded_evidence = []
        for ev in evidence_list:
            # Create a clone of the evidence object
            new_graph_nodes = set(ev.graph_node_ids)
            new_table_ids = set(ev.table_ids)
            new_entity_ids = set(ev.entity_ids)
            new_layout_ids = set(ev.layout_ids)

            # Perform 1-hop expansion for each graph node in the evidence
            for node_id in list(new_graph_nodes):
                connections = graph_connections.get(node_id, [])
                for conn in connections:
                    target = conn["target"]
                    conn_type = conn["type"]
                    
                    # 1. Expand along structural edges: parent_child, next/prev, contains, caption_of
                    if conn_type in ["parent_child", "next", "previous", "contains", "caption_of"]:
                        new_graph_nodes.add(target)
                    
                    # 2. Check if connection is a table relation
                    if conn_type == "caption_of" and target.startswith("tbl"):
                        new_table_ids.add(target)

            # Convert sets back to list properties
            ev.graph_node_ids = list(new_graph_nodes)
            ev.table_ids = list(new_table_ids)
            ev.entity_ids = list(new_entity_ids)
            ev.layout_ids = list(new_layout_ids)
            
            expanded_evidence.append(ev)

        return expanded_evidence
