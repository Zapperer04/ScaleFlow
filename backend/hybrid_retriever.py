import threading
from typing import List, Dict, Any, Optional
from services.vector_store import search_similar, get_client
from services.embedding_service import embed_text
from services.bm25_service import retrieve_bm25
from document_graph import DocumentGraph
from graph_retriever import GraphRetriever

class HybridRetriever:
    def __init__(self, traversal_depth: int = 1):
        self.graph_retriever = GraphRetriever(traversal_depth=traversal_depth)

    def retrieve(self, query: str, pipeline_id: int, top_k: int = 10, filters: Optional[Dict[str, Any]] = None, graph: Optional[DocumentGraph] = None) -> List[Dict[str, Any]]:
        semantic_results = []
        bm25_results = []
        
        # Parallel execution of Semantic and BM25 retrievals
        def run_semantic():
            nonlocal semantic_results
            try:
                query_vec = embed_text(query)
                # filters format for Qdrant
                from qdrant_client.http import models as qmodels
                q_filters = qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="pipeline_id",
                            match=qmodels.MatchValue(value=pipeline_id)
                        )
                    ]
                )
                if filters:
                    for k, v in filters.items():
                        if k != "pipeline_id":
                            q_filters.must.append(
                                qmodels.FieldCondition(
                                    key=k,
                                    match=qmodels.MatchValue(value=v)
                                )
                            )
                points = search_similar(
                    collection_name="scaleflow_chunks",
                    query_vector=query_vec,
                    top_k=top_k,
                    filters=q_filters
                )
                for pt in points:
                    semantic_results.append({
                        "chunk_id": pt.payload.get("chunk_id"),
                        "text": pt.payload.get("chunk_text") or pt.payload.get("text"),
                        "score": pt.score,
                        "payload": pt.payload
                    })
            except Exception as e:
                print(f"[HYBRID RETRIEVER] Semantic search failed: {e}", flush=True)

        def run_bm25():
            nonlocal bm25_results
            try:
                bm25_hits = retrieve_bm25(pipeline_id=pipeline_id, query=query, top_k=top_k)
                for hit in bm25_hits:
                    # Apply local filters if matching file_id etc.
                    if filters:
                        match = True
                        for k, v in filters.items():
                            if hit.get(k) != v and hit.get("metadata", {}).get(k) != v:
                                match = False
                                break
                        if not match:
                            continue
                    bm25_results.append(hit)
            except Exception as e:
                print(f"[HYBRID RETRIEVER] BM25 search failed: {e}", flush=True)

        t1 = threading.Thread(target=run_semantic)
        t2 = threading.Thread(target=run_bm25)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # Merge pool and establish provenance map
        candidates = {}

        # 1. Process Semantic Hits
        for hit in semantic_results:
            cid = hit["chunk_id"]
            payload = hit["payload"]
            candidates[cid] = {
                "chunk_id": cid,
                "text": hit["text"],
                "sources": ["semantic"],
                "semantic_score": hit["score"],
                "bm25_score": 0.0,
                "graph_score": 0.0,
                "graph_depth": 99,
                "graph_priority": 0.0,
                "chunk": payload
            }

        # 2. Process BM25 Hits
        for hit in bm25_results:
            cid = hit.get("chunk_id")
            if not cid:
                continue
            score = hit.get("score", 0.0)
            if cid in candidates:
                candidates[cid]["sources"].append("bm25")
                candidates[cid]["bm25_score"] = score
            else:
                candidates[cid] = {
                    "chunk_id": cid,
                    "text": hit.get("chunk_text") or hit.get("text"),
                    "sources": ["bm25"],
                    "semantic_score": 0.0,
                    "bm25_score": score,
                    "graph_score": 0.0,
                    "graph_depth": 99,
                    "graph_priority": 0.0,
                    "chunk": hit
                }

        # 3. Process Graph Traversal context expansion
        if graph:
            # Gather starting node IDs from semantic and bm25 hits
            start_nodes = []
            for cid, cand in candidates.items():
                node_ids = cand["chunk"].get("graph_node_ids") or cand["chunk"].get("metadata", {}).get("graph_node_ids", [])
                if isinstance(node_ids, str):
                    node_ids = [node_ids]
                start_nodes.extend(node_ids)
                
            # Perform traversal
            graph_res = self.graph_retriever.retrieve(graph, query, start_node_ids=list(set(start_nodes)))
            
            # Map retrieved graph nodes back to chunks
            # Find any chunks in Qdrant or locally matching these graph nodes
            # To be efficient, we can search the candidate pool, and also assign graph_score/graph_depth/graph_priority.
            # If a chunk corresponds to retrieved graph nodes, we elevate it
            for node in graph_res.nodes:
                node_id = node["id"]
                # Look for chunks referencing this node
                for cid, cand in candidates.items():
                    c_node_ids = cand["chunk"].get("graph_node_ids") or cand["chunk"].get("metadata", {}).get("graph_node_ids", [])
                    if node_id in c_node_ids:
                        if "graph" not in cand["sources"]:
                            cand["sources"].append("graph")
                        cand["graph_score"] = 1.0
                        cand["graph_depth"] = min(cand["graph_depth"], 1) # simple depth representation
                        cand["graph_priority"] = 1.0

        return list(candidates.values())
