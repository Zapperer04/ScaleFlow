import uuid
from typing import List, Dict, Any, Optional

class DocumentGraph:
    def __init__(self, document_id: str, version: int = 1, schema: str = "document-graph-v1"):
        self.version = version
        self.schema = schema
        self.document_id = document_id
        self.pages = []
        self.nodes = []
        self.edges = []
        
        # Fast lookup indices
        self._node_by_id = {}
        self._edges_by_source = {}
        self._edges_by_target = {}

    def add_page(self, page_number: int, width: float, height: float, metadata: Optional[Dict[str, Any]] = None):
        page_info = {
            "page_number": page_number,
            "width": width,
            "height": height,
            "metadata": metadata or {}
        }
        self.pages.append(page_info)
        return page_info

    def add_node(self, node_id: str, node_type: str, page: int, text: str, 
                 bbox: Optional[Dict[str, float]] = None, parent: Optional[str] = None, 
                 children: Optional[List[str]] = None, reading_order: int = 0, 
                 metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        node = {
            "id": node_id,
            "type": node_type,  # page, section, paragraph, table, figure, caption, list, header, footer, reference, etc.
            "page": page,
            "bbox": bbox,       # e.g. {"ymin": 0.0, "xmin": 0.0, "ymax": 1.0, "xmax": 1.0}
            "text": text,
            "parent": parent,
            "children": children or [],
            "reading_order": reading_order,
            "metadata": metadata or {}
        }
        self.nodes.append(node)
        self._node_by_id[node_id] = node
        
        # Maintain parent-child reference integrity
        if parent and parent in self._node_by_id:
            parent_node = self._node_by_id[parent]
            if node_id not in parent_node["children"]:
                parent_node["children"].append(node_id)
                
        return node

    def add_edge(self, source: str, target: str, edge_type: str, 
                 metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        # edge_type: contains, left_of, right_of, above, below, next, previous, caption_of, references
        edge = {
            "source": source,
            "target": target,
            "type": edge_type,
            "metadata": metadata or {}
        }
        self.edges.append(edge)
        
        self._edges_by_source.setdefault(source, []).append(edge)
        self._edges_by_target.setdefault(target, []).append(edge)
        return edge

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        return self._node_by_id.get(node_id)

    def get_outbound_edges(self, node_id: str) -> List[Dict[str, Any]]:
        return self._edges_by_source.get(node_id, [])

    def get_inbound_edges(self, node_id: str) -> List[Dict[str, Any]]:
        return self._edges_by_target.get(node_id, [])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "schema": self.schema,
            "document_id": self.document_id,
            "pages": self.pages,
            "nodes": self.nodes,
            "edges": self.edges
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentGraph":
        graph = cls(
            document_id=data.get("document_id", str(uuid.uuid4())),
            version=data.get("version", 1),
            schema=data.get("schema", "document-graph-v1")
        )
        graph.pages = data.get("pages", [])
        
        # Load nodes and index them
        for node in data.get("nodes", []):
            graph.nodes.append(node)
            graph._node_by_id[node["id"]] = node

        # Load edges and index them
        for edge in data.get("edges", []):
            graph.edges.append(edge)
            src = edge["source"]
            tgt = edge["target"]
            graph._edges_by_source.setdefault(src, []).append(edge)
            graph._edges_by_target.setdefault(tgt, []).append(edge)
            
        return graph
