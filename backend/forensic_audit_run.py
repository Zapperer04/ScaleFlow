import os
import sys
import json
import math

# Adjust path to find backend modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import config
from services.chunking_service import chunk_document_graph
from services.vector_store import get_client
import qdrant_client.models as qmodels
from services.retrieval_service import retrieve_and_rerank
from services.llm_service import generate_answer
from services.embedding_service import embed_text

# Load document graph copy
with open("document_graph_copy.json", "r", encoding="utf-8") as f:
    raw_doc_graph = json.load(f)
doc_graph = raw_doc_graph.get("document_graph") or raw_doc_graph

print("==================== PHASE 1: DOCUMENT GRAPH QUALITY ====================")
pages = doc_graph.get("pages", [])
first_page = pages[0] if pages else {}
nodes = first_page.get("nodes", [])
edges = first_page.get("edges", [])

print(f"Total Nodes: {len(nodes)}")
print(f"Total Edges: {len(edges)}")
node_types = sorted(list(set(n.get("type", "unknown") for n in nodes)))
print(f"Node Types: {node_types}")
section_labels = sorted(list(set(n.get("section", "unknown") for n in nodes)))
print(f"Section Labels: {section_labels}")
print(f"Graph Metadata: {doc_graph.get('metadata', {})}")
print(f"Page Metadata: Width={first_page.get('width')}, Height={first_page.get('height')}")

print("\n--- NODES DUMP ---")
for idx, n in enumerate(nodes):
    print(json.dumps({
        "chunk_id": n.get("chunk_id"),
        "node_type": n.get("type"),
        "section": n.get("section"),
        "text": n.get("text", "")[:100] + "...",
        "bbox": n.get("bbox"),
        "neighbors": n.get("neighbors"),
        "semantic_parent": n.get("semantic_parent"),
        "metadata": n.get("metadata")
    }, indent=2))


print("==================== PHASE 2: CHUNKING QUALITY ====================")
chunk_res = chunk_document_graph(doc_graph)
chunks = chunk_res.get("chunks", [])
print(f"Total Chunks: {len(chunks)}")
print("\n--- CHUNKS DUMP ---")
for idx, c in enumerate(chunks):
    print(json.dumps({
        "chunk_index": idx,
        "chunk_text": c.get("text", "")[:100] + "...",
        "section": c.get("metadata", {}).get("section"),
        "node_type": c.get("metadata", {}).get("node_type"),
        "semantic_parent": c.get("metadata", {}).get("semantic_parent"),
        "neighbors": c.get("metadata", {}).get("neighbors", []),
        "metadata": c.get("metadata", {})
    }, indent=2))


print("==================== PHASE 3: QDRANT STORAGE AUDIT ====================")
client = get_client()
collection_name = config.QDRANT_COLLECTION_NAME
print(f"Qdrant collection: {collection_name}")
try:
    res, _ = client.scroll(
        collection_name=collection_name,
        scroll_filter=qmodels.Filter(
            must=[qmodels.FieldCondition(key="pipeline_id", match=qmodels.MatchValue(value=549))]
        ),
        limit=100,
        with_payload=True,
        with_vectors=True
    )
    print(f"Found {len(res)} points for pipeline 549 in Qdrant")
    for pt in res:
        payload = pt.payload or {}
        vector = pt.vector or []
        print(json.dumps({
            "id": pt.id,
            "payload": {k: (v[:100] + "..." if isinstance(v, str) and len(v) > 100 else v) for k, v in payload.items()},
            "vector_size": len(vector) if isinstance(vector, list) else "unknown",
            "metadata": {
                "section_exists": "section" in payload,
                "node_type_exists": "content_type" in payload or "node_type" in payload,
                "semantic_parent_exists": "semantic_parent" in payload,
                "neighbors_exist": "neighbors" in payload,
                "pipeline_id_exists": "pipeline_id" in payload,
                "document_id_exists": "document_id" in payload or "file_id" in payload
            }
        }, indent=2))
except Exception as e:
    print(f"Qdrant error: {e}")


print("==================== PHASES 4-8: AUDIT QUERIES RUNNER ====================")
queries = [
    "who are the inventors",
    "what is this patent about",
    "in which country is this patent valid in",
    "what problem does this invention solve",
    "how does this invention improve farming productivity",
    "who owns this patent",
    "what are the major features of this invention"
]

for q in queries:
    print(f"\n========================================\nQUERY: {q}\n========================================")
    try:
        q_vec = embed_text(q)
        ret_res = retrieve_and_rerank(q_vec, query=q, pipeline_id=549, top_k=5)
        # Trace retrieval candidates
        results = ret_res.get("results", [])
        print("RETRIEVED CANDIDATES AFTER EXPANSION & RERANKING:")
        for r in results:
            print(json.dumps({
                "chunk_id": r.get("chunk_id"),
                "dense_score": r.get("dense_score"),
                "bm25_score": r.get("bm25_score"),
                "rerank_score": r.get("rerank_score"),
                "final_score": r.get("score"),
                "section": r.get("section"),
                "text": r.get("chunk_text", r.get("text", ""))[:120] + "..."
            }, indent=2))
        
        # Simulate LLM Call context
        context_text = ""
        for idx, c in enumerate(results[:3]):
            text = c.get("chunk_text") or c.get("text") or ""
            context_text += f"[Source {idx+1}]: {text}\n\n"
        print("\nEXACT CONTEXT WINDOW FOR LLM:")
        print(context_text[:1000] + "...")

        # Run LLM Generation
        ans, provider, status = generate_answer(q, results[:3])
        print(f"\nGENERATED ANSWER ({provider}):")
        print(ans)
    except Exception as e:
        print(f"Error executing query flow: {e}")
