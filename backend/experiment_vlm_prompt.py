import os
import sys
import json
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from services.document_preprocessor import DocumentPreprocessor, _call_gemini_page_parser, execute_vlm_document_graph_extraction

# Setup target PDF
pdf_path = r"storage/uploads/178_PBL_Patent.pdf"

# Initialize preprocessor and render page 1
dp = DocumentPreprocessor(pdf_path)
images = dp.render_document(max_pages=1, dpi=300)
img = images[0]

# Run VLM parsing using our newly updated prompt schema
print("\n=== Running Phase 6 VLM Semantic Parser ===")
t0 = time.perf_counter()
graph = execute_vlm_document_graph_extraction([img], pipeline_id="phase_6_test", max_workers=1)
t1 = time.perf_counter()
duration = t1 - t0

if not graph or not graph.get("pages"):
    print("Error: Graph extraction returned empty results!")
    sys.exit(1)

page = graph["pages"][0]
nodes = page.get("nodes", [])
edges = page.get("edges", [])

print("\n=== 1. Raw Parser Output (First 20 Nodes) ===")
dumped_nodes = []
for n in nodes[:20]:
    dumped_nodes.append({
        "node_id": n.get("node_id"),
        "text": n.get("text")[:80] + "..." if n.get("text") else "",
        "structural_type": n.get("structural_type"),
        "semantic_category": n.get("semantic_category"),
        "entity_group": n.get("entity_group"),
        "confidence": n.get("confidence"),
        "reading_order": n.get("reading_order"),
        "bbox": n.get("bbox")
    })
print(json.dumps(dumped_nodes, indent=2))

print("\n=== 2. Semantic Category Statistics ===")
semantic_stats = {}
for n in nodes:
    cat = n.get("semantic_category") or "unknown"
    semantic_stats[cat] = semantic_stats.get(cat, 0) + 1
print(json.dumps(semantic_stats, indent=2))

print("\n=== 3. Entity Group Statistics ===")
groups = [n.get("entity_group") for n in nodes if n.get("entity_group") and n.get("entity_group") != "unknown"]
unique_groups = set(groups)
group_counts = [groups.count(g) for g in unique_groups]

group_stats = {
    "groups": len(unique_groups),
    "avg_nodes_per_group": round(sum(group_counts) / len(group_counts), 1) if group_counts else 0,
    "max_nodes_per_group": max(group_counts) if group_counts else 0
}
print(json.dumps(group_stats, indent=2))

print("\n=== 4. Confidence Statistics ===")
confidences = [n.get("confidence") for n in nodes if n.get("confidence") is not None]
conf_stats = {
    "mean": round(sum(confidences) / len(confidences), 2) if confidences else 0,
    "median": round(sorted(confidences)[len(confidences)//2], 2) if confidences else 0,
    "min": min(confidences) if confidences else 0
}
print(json.dumps(conf_stats, indent=2))

print("\n=== 5. Retrieval Metadata Verification ===")
print("Total parsed nodes:", len(nodes))
print("Total edges generated:", len(edges))
print(f"Total processing latency: {duration:.2f} seconds")
