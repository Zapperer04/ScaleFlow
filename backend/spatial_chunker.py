import hashlib
from typing import List, Dict, Any, Optional

def compute_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

class SpatialChunker:
    def __init__(self, max_tokens: int = 512):
        self.max_tokens = max_tokens

    def chunk_document(self, graph_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
        document_id = graph_dict.get("document_id", "default_doc")
        nodes = graph_dict.get("nodes", [])
        
        # Sort nodes by reading order / sequence
        sorted_nodes = sorted(nodes, key=lambda n: (n.get("page", 1), n.get("reading_order", 0)))
        
        chunks = []
        current_paragraphs = []
        current_node_ids = []
        current_section = "unknown"
        current_heading = ""
        current_page = None
        
        def finalize_chunk(text: str, page: int, node_ids: List[str], section: str, heading: str, bbox: Optional[Dict[str, float]] = None):
            if not text.strip():
                return
            word_count = len(text.split())
            chunk_idx = len(chunks) + 1
            chunk_id = f"chunk_{document_id}_{chunk_idx}"
            
            # Combine bounding boxes of contributing nodes if not explicitly provided
            if not bbox and node_ids:
                ymin, xmin, ymax, xmax = 1.0, 1.0, 0.0, 0.0
                has_bbox = False
                for nid in node_ids:
                    node = next((n for n in nodes if n["id"] == nid), None)
                    if node and node.get("bbox"):
                        nb = node["bbox"]
                        ymin = min(ymin, nb.get("ymin", nb.get("y1", 0.0)))
                        xmin = min(xmin, nb.get("xmin", nb.get("x1", 0.0)))
                        ymax = max(ymax, nb.get("ymax", nb.get("y2", 1.0)))
                        xmax = max(xmax, nb.get("xmax", nb.get("x2", 1.0)))
                        has_bbox = True
                bbox = {"ymin": ymin, "xmin": xmin, "ymax": ymax, "xmax": xmax} if has_bbox else {"ymin": 0, "xmin": 0, "ymax": 1, "xmax": 1}

            chunk = {
                "chunk_id": chunk_id,
                "document_id": document_id,
                "page": page,
                "section_id": section,
                "heading": heading,
                "graph_node_ids": node_ids,
                "bbox": bbox,
                "text": text,
                "token_count": word_count, # simple word count as token estimator
                "embedding_id": f"embed_{chunk_id}_{compute_hash(text)[:8]}",
                "bm25_doc_id": f"bm25_{chunk_id}_{compute_hash(text)[:8]}",
                "metadata": {
                    "document_id": document_id,
                    "page": page,
                    "section_id": section,
                    "heading": heading
                }
            }
            chunks.append(chunk)

        for node in sorted_nodes:
            node_type = node.get("type", "paragraph")
            node_text = node.get("text", "")
            node_page = node.get("page", 1)
            node_id = node.get("id")
            
            # Update heading/section if node is heading/section
            if node_type == "heading" or node_type == "section":
                # Finalize any ongoing merged paragraph chunk before starting a new heading
                if current_paragraphs:
                    combined_text = "\n\n".join(current_paragraphs)
                    finalize_chunk(combined_text, current_page, current_node_ids, current_section, current_heading)
                    current_paragraphs = []
                    current_node_ids = []
                
                current_heading = node_text
                current_section = node_id
                current_page = node_page
                
                # Headings are finalized as their own chunks
                finalize_chunk(node_text, node_page, [node_id], current_section, current_heading, bbox=node.get("bbox"))
                continue

            # Switch pages: finalize active chunks first
            if current_page is not None and node_page != current_page:
                if current_paragraphs:
                    combined_text = "\n\n".join(current_paragraphs)
                    finalize_chunk(combined_text, current_page, current_node_ids, current_section, current_heading)
                    current_paragraphs = []
                    current_node_ids = []
            
            current_page = node_page

            # Never split: table, figure, caption, code block, equation
            if node_type in ["table", "figure", "caption", "code_block", "equation"]:
                # Finalize ongoing paragraph chunk first
                if current_paragraphs:
                    combined_text = "\n\n".join(current_paragraphs)
                    finalize_chunk(combined_text, current_page, current_node_ids, current_section, current_heading)
                    current_paragraphs = []
                    current_node_ids = []
                
                # Single node chunk
                finalize_chunk(node_text, node_page, [node_id], current_section, current_heading, bbox=node.get("bbox"))
            else:
                # Merge adjacent paragraphs, list items, footers, headers
                word_len = len(node_text.split())
                current_sum = sum(len(p.split()) for p in current_paragraphs)
                
                # Split oversized section paragraphs
                if current_paragraphs and (current_sum + word_len > self.max_tokens):
                    combined_text = "\n\n".join(current_paragraphs)
                    finalize_chunk(combined_text, current_page, current_node_ids, current_section, current_heading)
                    current_paragraphs = []
                    current_node_ids = []
                
                current_paragraphs.append(node_text)
                current_node_ids.append(node_id)

        # Final cleanup
        if current_paragraphs:
            combined_text = "\n\n".join(current_paragraphs)
            finalize_chunk(combined_text, current_page, current_node_ids, current_section, current_heading)

        return chunks
