from typing import List, Dict, Any, Optional, Set
from document_graph import DocumentGraph

class GraphRetrievalResult:
    def __init__(self, nodes: List[Dict[str, Any]], paths: List[List[str]], traversal_depth: int):
        self.nodes = nodes
        self.paths = paths
        self.traversal_depth = traversal_depth

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": self.nodes,
            "paths": self.paths,
            "traversal_depth": self.traversal_depth
        }

class GraphRetriever:
    def __init__(self, traversal_depth: int = 2):
        self.traversal_depth = traversal_depth

    def retrieve(self, graph: DocumentGraph, query: str, start_node_ids: Optional[List[str]] = None) -> GraphRetrievalResult:
        retrieved_nodes_map = {}
        visited = set()
        paths = []
        
        # 1. Identify starting nodes
        starts = []
        if start_node_ids:
            for nid in start_node_ids:
                node = graph.get_node(nid)
                if node:
                    starts.append(node)
                    
        # If no start nodes provided, find nodes matching keywords in the query
        if not starts and query:
            query_words = set(query.lower().split())
            for node in graph.nodes:
                node_text = node.get("text", "").lower()
                # Simple keyword overlap to seed starting nodes
                if any(word in node_text for word in query_words if len(word) > 3):
                    starts.append(node)
                    
        # 2. Traverse graph
        queue = []  # Elements are (node_id, depth, path_taken)
        for s in starts:
            queue.append((s["id"], 0, [s["id"]]))
            
        while queue:
            node_id, depth, path = queue.pop(0)
            if node_id in visited:
                continue
            visited.add(node_id)
            
            node = graph.get_node(node_id)
            if not node:
                continue
                
            retrieved_nodes_map[node_id] = node
            paths.append(path)
            
            if depth >= self.traversal_depth:
                continue
                
            # Traverse Parent and Children from Node attributes
            parent_id = node.get("parent")
            if parent_id and parent_id not in visited:
                queue.append((parent_id, depth + 1, path + [parent_id]))
                
            for child_id in node.get("children", []):
                if child_id not in visited:
                    queue.append((child_id, depth + 1, path + [child_id]))
                    
            # Traverse explicit edges (contains, caption_of, references, next, previous, next/prev siblings)
            for edge in graph.get_outbound_edges(node_id):
                tgt = edge["target"]
                if tgt not in visited:
                    queue.append((tgt, depth + 1, path + [tgt]))
                    
            for edge in graph.get_inbound_edges(node_id):
                src = edge["source"]
                if src not in visited:
                    queue.append((src, depth + 1, path + [src]))

        # Include siblings of retrieved paragraphs if depth > 0
        if self.traversal_depth > 0:
            for nid in list(retrieved_nodes_map.keys()):
                node = retrieved_nodes_map[nid]
                parent_id = node.get("parent")
                if parent_id:
                    parent_node = graph.get_node(parent_id)
                    if parent_node:
                        for sibling_id in parent_node.get("children", []):
                            if sibling_id not in retrieved_nodes_map:
                                sibling_node = graph.get_node(sibling_id)
                                if sibling_node:
                                    retrieved_nodes_map[sibling_id] = sibling_node
                                    paths.append([nid, sibling_id])

        return GraphRetrievalResult(
            nodes=list(retrieved_nodes_map.values()),
            paths=paths,
            traversal_depth=self.traversal_depth
        )
