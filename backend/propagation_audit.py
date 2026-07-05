import os
import sys
import json

# Adjust path to find backend modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
with open("document_graph_copy.json", "r", encoding="utf-8") as f:
    raw_data = json.load(f)

# The raw parser output parsed directly before normalization/graph assembly is in raw_data, 
# but let's check what keys are in raw_data
print("Raw Keys:", raw_data.keys())

# Step 1: Dump raw parser output.
# Since the raw Gemini JSON text might not be preserved, we can inspect normalized nodes as they exist
# inside pages[0]['nodes'] which corresponds directly to Step 1 & 2.
pages = raw_data.get("document_graph", {}).get("pages", [])
if not pages:
    pages = raw_data.get("pages", [])

nodes = pages[0].get("nodes", []) if pages else []
edges = pages[0].get("edges", []) if pages else []

print("=== Step 1: Dump raw parser nodes ===")
print("Parser nodes found:", len(nodes))
dumped = []
for n in nodes[:20]:
    # We reconstruct/dump properties
    d = {
        "node_id": n.get("chunk_id"),
        "text": n.get("text")[:100] + "..." if n.get("text") else "",
        "node_type": n.get("type"),
        "semantic_type": n.get("type"), # mapped directly
        "section": n.get("section"),
        "label": n.get("section"),
        "bbox": n.get("bbox"),
        "metadata": n.get("metadata")
    }
    dumped.append(d)
print(json.dumps(dumped, indent=2))

print("\n=== Step 2: Dump document graph nodes (propagated) ===")
# For same nodes:
dumped_graph = []
for n in nodes[:20]:
    d = {
        "node_id": n.get("chunk_id"),
        "text": n.get("text")[:100] + "..." if n.get("text") else "",
        "node_type": n.get("type"),
        "section": n.get("section"),
        "semantic_parent": n.get("semantic_parent"),
        "neighbors": n.get("neighbors"),
        "metadata": n.get("metadata")
    }
    dumped_graph.append(d)
print(json.dumps(dumped_graph, indent=2))

print("\n=== Step 3: Semantic retention statistics ===")
nodes_total = len(nodes)
nodes_with_section = sum(1 for n in nodes if n.get("section"))
nodes_with_semantic_type = sum(1 for n in nodes if n.get("type"))
nodes_with_metadata = sum(1 for n in nodes if n.get("metadata"))
nodes_with_neighbors = sum(1 for n in nodes if n.get("neighbors"))
nodes_with_parent = sum(1 for n in nodes if n.get("semantic_parent"))
nodes_labeled_unknown = sum(1 for n in nodes if n.get("section") == "unknown")

stats = {
    "nodes_total": nodes_total,
    "nodes_with_section": nodes_with_section,
    "nodes_with_semantic_type": nodes_with_semantic_type,
    "nodes_with_metadata": nodes_with_metadata,
    "nodes_with_neighbors": nodes_with_neighbors,
    "nodes_with_parent": nodes_with_parent,
    "nodes_labeled_unknown": nodes_labeled_unknown
}
print(json.dumps(stats, indent=2))

print("\n=== Step 4: Graph semantics ===")
edge_count = len(edges)
semantic_edges = sum(1 for e in edges if e.get("relation") not in ("NEXT", "PAGE_NEXT") and not e.get("relation", "").startswith("SPATIAL"))
spatial_edges = sum(1 for e in edges if e.get("relation", "").startswith("SPATIAL"))
reading_order_edges = sum(1 for e in edges if e.get("relation") == "NEXT")
cross_reference_edges = sum(1 for e in edges if e.get("relation") == "CROSS_REF")

edge_stats = {
    "edge_count": edge_count,
    "semantic_edges": semantic_edges,
    "spatial_edges": spatial_edges,
    "reading_order_edges": reading_order_edges,
    "cross_reference_edges": cross_reference_edges
}
print(json.dumps(edge_stats, indent=2))
