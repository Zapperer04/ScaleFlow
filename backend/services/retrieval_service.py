"""
retrieval_service.py — Graph‑native hybrid retrieval orchestrator for ScaleFlow.

Orchestrates:
    intent detection → dense retrieval (vector_store) + BM25 retrieval (bm25_service)
    → merge → graph expansion (graph_expansion_service) → importance boost
    → cross‑encoder rerank (reranker_service) → results.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

from services.vector_store import search_similar
from services.bm25_service import retrieve_bm25
from services.graph_expansion_service import expand_graph_context
from services.reranker_service import rerank

logger = logging.getLogger(__name__)

def _qdrant_chunk_lookup(pipeline_id: int, file_id: int, chunk_id: str) -> dict | None:
    try:
        from services.vector_store import get_client
        import qdrant_client.models as qmodels
        import config
        client = get_client()
        must_filters = [
            qmodels.FieldCondition(
                key="chunk_id",
                match=qmodels.MatchValue(value=chunk_id)
            )
        ]
        if pipeline_id is not None:
            must_filters.append(
                qmodels.FieldCondition(
                    key="pipeline_id",
                    match=qmodels.MatchValue(value=int(pipeline_id))
                )
            )
        res, _ = client.scroll(
            collection_name=config.QDRANT_COLLECTION_NAME,
            scroll_filter=qmodels.Filter(must=must_filters),
            limit=1,
            with_payload=True,
            with_vectors=False
        )
        if res:
            point = res[0]
            payload = dict(point.payload)
            payload["score"] = 1.0
            return payload
    except Exception as e:
        logger.warning(f"Qdrant chunk lookup failed for chunk {chunk_id}: {e}")
    return None

from services.graph_expansion_service import set_chunk_lookup
set_chunk_lookup(_qdrant_chunk_lookup)


# ------------------------------------------------------------------------------
# Query intent detection
# ------------------------------------------------------------------------------
INTENT_PATTERNS = {
    "factual": [
        r"\b(what|who|when|where|how many|how much)\b",
    ],
    "table": [
        r"\btable\b",
        r"\bchart\b",
        r"\bgraph\b",
        r"\brows?\b",
        r"\bcolumns?\b",
    ],
    "entity": [
        r"\b(who is|company|organization|person)\b",
        r"\bdate of\b",
        r"\bnumber of\b",
    ],
    "citation": [
        r"\bcite\b",
        r"\breference\b",
        r"\baccording to\b",
        r"\bstudy\b",
    ],
    "structural": [
        r"\bchapter\b",
        r"\bsection\b",
        r"\bheading\b",
        r"\boutline\b",
    ],
    "summary": [
        r"\bsummary\b",
        r"\boverview\b",
        r"\babstract\b",
    ],
    "figure": [
        r"\bfigure\b",
        r"\bimage\b",
        r"\bdiagram\b",
        r"\bpicture\b",
    ],
    "equation": [
        r"\bequation\b",
        r"\bformula\b",
        r"\beq\.?\b",
    ],
    "comparison": [
        r"\bcompare\b",
        r"\bdifference between\b",
        r"\bversus\b",
    ],
}


def detect_query_intent(query: str) -> List[str]:
    """
    Classify query into one or more intents and map to Qdrant collections.
    """
    if not query:
        return [config.QDRANT_COLLECTION_NAME]

    query_lower = query.lower()
    detected_intents = []
    for intent, patterns in INTENT_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, query_lower):
                detected_intents.append(intent)
                break
    if not detected_intents:
        detected_intents = ["factual"]

    # Map intents to collections
    collection_map = {
        "factual": config.QDRANT_PARAGRAPH_COLLECTION,
        "table": config.QDRANT_TABLE_COLLECTION,
        "entity": config.QDRANT_COLLECTION_NAME,
        "citation": config.QDRANT_COLLECTION_NAME,
        "structural": config.QDRANT_COLLECTION_NAME,
        "summary": config.QDRANT_COLLECTION_NAME,
        "figure": config.QDRANT_COLLECTION_NAME,
        "equation": config.QDRANT_COLLECTION_NAME,
        "comparison": config.QDRANT_COLLECTION_NAME,
    }
    collections = list(set(collection_map.get(i, config.QDRANT_COLLECTION_NAME) for i in detected_intents))
    logger.info(f"[INTENT] Query intent(s): {detected_intents} → collections: {collections}")
    return collections


# ------------------------------------------------------------------------------
# Dense retrieval wrapper
# ------------------------------------------------------------------------------
def retrieve_dense(
    query_vector: list,
    collection_name: str,
    top_k: int = 30,
    filters: Optional[Dict] = None,
) -> List[Dict]:
    """
    Perform dense vector similarity search via vector_store.
    Adds 'dense_score' field to every result.
    """
    results = search_similar(
        collection_name=collection_name,
        query_vector=query_vector,
        top_k=top_k,
        filters=filters,
    )
    for r in results:
        r["dense_score"] = r.get("score", 0.0)
    return results


# ------------------------------------------------------------------------------
# Hybrid candidate merging
# ------------------------------------------------------------------------------
def merge_candidates(
    dense_candidates: List[Dict],
    bm25_candidates: List[Dict],
    dense_weight: float = 0.6,
    bm25_weight: float = 0.4,
) -> List[Dict]:
    """
    Merge dense and BM25 candidates, deduplicate by (pipeline_id, file_id, chunk_id),
    and compute a hybrid_score.
    """
    merged: Dict[tuple, Dict] = {}
    for cand in dense_candidates:
        key = (cand.get("pipeline_id"), cand.get("file_id"), cand.get("chunk_id"))
        if key not in merged:
            merged[key] = dict(cand)
            merged[key]["hybrid_score"] = cand.get("dense_score", 0.0) * dense_weight
        else:
            merged[key]["hybrid_score"] += cand.get("dense_score", 0.0) * dense_weight

    for cand in bm25_candidates:
        key = (cand.get("pipeline_id"), cand.get("file_id"), cand.get("chunk_id"))
        # Extract BM25 score explicitly
        bm25_score = cand.get("retrieval_score", cand.get("score", 0.0))
        if key not in merged:
            merged[key] = dict(cand)
            merged[key]["hybrid_score"] = bm25_score * bm25_weight
        else:
            merged[key]["hybrid_score"] += bm25_score * bm25_weight

    return list(merged.values())


# ------------------------------------------------------------------------------
# Importance boost
# ------------------------------------------------------------------------------
def apply_importance_boost(candidates: List[Dict]) -> List[Dict]:
    """
    Add importance_score * 0.15 and graph_score to hybrid_score to get final_score.
    """
    for cand in candidates:
        importance = cand.get("importance_score", 0.0)
        graph_score = cand.get("graph_score", 0.0)
        cand["final_score"] = cand.get("hybrid_score", 0.0) + importance * 0.15 + graph_score
    return candidates


# ------------------------------------------------------------------------------
# Main retrieval‑and‑rerank orchestrator
# ------------------------------------------------------------------------------
def retrieve_and_rerank(
    query_vector: list,
    pipeline_id: int = None,
    top_k: int = 5,
    query: str = "",
) -> dict:
    """
    Graph‑native hybrid retrieval pipeline.

    Steps:
        1. Intent detection & collection selection
        2. Dense retrieval from relevant collections
        3. BM25 retrieval from pipeline‑specific index
        4. Merge with hybrid scoring
        5. Graph expansion (neighbors, parent, children, cross‑refs)
        6. Importance boost
        7. Cross‑encoder rerank
        8. Return results with statistics
    """
    logger.info(f"[RETRIEVAL] Starting hybrid retrieval for query: '{query}'")

    # 1. Intent & collections
    collections = detect_query_intent(query)
    print(f"[RETRIEVAL] SEARCHING COLLECTIONS: {collections} for query: '{query}'", flush=True)

    # Filters for dense retrieval (optional pipeline filter)
    filters = {"pipeline_id": pipeline_id} if pipeline_id is not None else None

    recall_limit = max(top_k * 5, 30)

    # 2. Dense retrieval
    all_dense_candidates = []
    for coll in collections:
        dense_res = retrieve_dense(query_vector, coll, top_k=recall_limit, filters=filters)
        all_dense_candidates.extend(dense_res)

    # 3. BM25 retrieval
    all_bm25_candidates = []
    if pipeline_id is not None and query:
        try:
            bm25_res = retrieve_bm25(pipeline_id, query, top_k=recall_limit)
            all_bm25_candidates.extend(bm25_res)
        except Exception as e:
            logger.warning(f"BM25 retrieval failed: {e}")

    if not all_dense_candidates and not all_bm25_candidates:
        return {"query": query, "results": [], "statistics": {}}

    # 4. Merge
    merged = merge_candidates(all_dense_candidates, all_bm25_candidates)
    logger.info(f"[HYBRID] Merged {len(merged)} unique candidates")

    # 5. Graph expansion
    try:
        expanded = expand_graph_context(
            top_chunks=merged,
            pipeline_id=pipeline_id,
            limit=recall_limit,
        )
    except Exception as e:
        logger.warning(f"Graph expansion failed: {e}. Continuing with merged candidates.")
        expanded = merged
    logger.info(f"[GRAPH] Expanded to {len(expanded)} candidates (net new: {max(0, len(expanded) - len(merged))})")

    # 6. Importance boost
    boosted = apply_importance_boost(expanded)
    logger.info(f"[SCORE] Applied importance boost")

    # 7. Sort by final_score and take top for reranker
    boosted.sort(key=lambda x: x.get("final_score", 0.0), reverse=True)
    candidates_for_rerank = boosted[:max(recall_limit, top_k * 3)]

    # 8. Cross‑encoder rerank
    reranked = rerank(query, candidates_for_rerank, top_k=top_k)
    logger.info(f"[RERANK] Reranked down to {len(reranked)} results")

    # 9. Group-expansion for structured entity lists (e.g. inventors, applicants, authors)
    special_sections = {"inventor_info", "inventors", "applicant_info", "applicants", "author_info", "authors"}
    top_sections = {r.get("section", "").lower() for r in reranked[:2] if r.get("section")}
    matching_special = top_sections.intersection(special_sections)
    if matching_special:
        added_keys = {(r.get("pipeline_id"), r.get("file_id"), r.get("chunk_id")) for r in reranked}
        for cand in candidates_for_rerank:
            c_sec = cand.get("section", "").lower()
            if c_sec in matching_special:
                key = (cand.get("pipeline_id"), cand.get("file_id"), cand.get("chunk_id"))
                if key not in added_keys:
                    reranked.append(cand)
                    added_keys.add(key)
        logger.info(f"[ENTITY GROUPING] Expanded to {len(reranked)} chunks to include all entities in section: {matching_special}")

    # Print debug log for evaluation
    logger.info(
        f"\n==================== RETRIEVAL FLOW EVALUATION ====================\n"
        f"Query: {query}\n"
        f"Retrieved candidate count: {len(merged)}\n"
        f"Expanded candidate count: {len(expanded)}\n"
        f"Reranked candidate count: {len(reranked)}\n"
        f"Final context chunks: {[c.get('chunk_id') for c in reranked]}\n"
        f"===================================================================\n"
    )

    # 10. Calibrate score for UI presentation (use dense_score representing cosine similarity)
    for r in reranked:
        r["score"] = r.get("dense_score") or r.get("score", 0.0)

    # Compute statistics – graph expansion count is net new
    graph_expansion_count = max(0, len(expanded) - len(merged))

    statistics = {
        "intent": str(collections),
        "dense_candidates": len(all_dense_candidates),
        "bm25_candidates": len(all_bm25_candidates),
        "merged_candidates": len(merged),
        "graph_expansion_count": graph_expansion_count,
        "reranked_candidates": len(reranked),
    }
    logger.info(f"[CONTEXT] Final context size: {len(reranked)}")

    return {
        "query": query,
        "results": reranked,
        "statistics": statistics,
    }


# ------------------------------------------------------------------------------
# Backward‑compatible wrapper
# ------------------------------------------------------------------------------
def retrieve_context(
    query_vector: list,
    pipeline_id: int,
    top_k: int = None,
    query: str = "",
) -> dict:
    """
    Legacy wrapper around retrieve_and_rerank.
    """
    if top_k is None:
        top_k = config.DEFAULT_RETRIEVAL_TOP_K
    return retrieve_and_rerank(
        query_vector=query_vector,
        pipeline_id=pipeline_id,
        top_k=top_k,
        query=query,
    )


# ------------------------------------------------------------------------------
# Module exports
# ------------------------------------------------------------------------------
__all__ = [
    "retrieve_context",
    "retrieve_and_rerank",
    "detect_query_intent",
    "retrieve_dense",
    "merge_candidates",
    "apply_importance_boost",
]