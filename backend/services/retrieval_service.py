"""
retrieval_service.py — Graph‑native hybrid retrieval orchestrator for ScaleFlow.

Orchestrates:
    intent detection → dense retrieval + BM25 retrieval
    → RRF merge → cross‑encoder rerank → graph expansion
    → entity expansion → final rerank → results.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

from services.vector_store import search_similar, get_client
from services.bm25_service import retrieve_bm25
from services.graph_expansion_service import expand_graph_context
from services.reranker_service import rerank

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# Qdrant chunk lookup (for graph expansion)
# ------------------------------------------------------------------------------
def _qdrant_chunk_lookup(pipeline_id: int, file_id: int, chunk_id: str) -> dict | None:
    try:
        import qdrant_client.models as qmodels
        # NOTE (Deferred DI): retrieval_service.py is a flat functional module.
        # Full class-based VectorStore injection deferred to a future refactor.
        # See: docs/architecture/adr/007_constructor_dependency_injection_only.md
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

# NOTE: For large‑scale usage, graph_expansion_service should be updated to
# use batch lookups to avoid N+1 queries.

# ------------------------------------------------------------------------------
# Query intent detection (enhanced patterns)
# ------------------------------------------------------------------------------
INTENT_PATTERNS = {
    "factual": [
        r"\b(what|who|when|where|how many|how much|which|why|does|is|are|was|were)\b",
    ],
    "table": [
        r"\btable\b",
        r"\bchart\b",
        r"\bgraph\b",
        r"\brows?\b",
        r"\bcolumns?\b",
        r"\bmatrix\b",
        r"\bdata\b",
        r"\bstatistics?\b",
    ],
    "entity": [
        r"\b(who is|company|organization|person|founder|ceo|president|director)\b",
        r"\bdate of\b",
        r"\bnumber of\b",
        r"\bname of\b",
    ],
    "citation": [
        r"\bcite\b",
        r"\breference\b",
        r"\baccording to\b",
        r"\bstudy\b",
        r"\bresearch\b",
        r"\bpaper\b",
    ],
    "structural": [
        r"\bchapter\b",
        r"\bsection\b",
        r"\bheading\b",
        r"\boutline\b",
        r"\btoc\b",
        r"\bappendix\b",
    ],
    "summary": [
        r"\bsummary\b",
        r"\boverview\b",
        r"\babstract\b",
        r"\bsynopsis\b",
        r"\brecap\b",
    ],
    "figure": [
        r"\bfigure\b",
        r"\bimage\b",
        r"\bdiagram\b",
        r"\bpicture\b",
        r"\bphoto\b",
        r"\billustration\b",
    ],
    "equation": [
        r"\bequation\b",
        r"\bformula\b",
        r"\beq\.?\b",
        r"\bmathematical\b",
    ],
    "comparison": [
        r"\bcompare\b",
        r"\bdifference between\b",
        r"\bversus\b",
        r"\bvs\.?\b",
        r"\bsimilarity\b",
    ],
    "definition": [
        r"\bdefine\b",
        r"\bmeaning of\b",
        r"\bdefinition\b",
    ],
    "cause_effect": [
        r"\bbecause\b",
        r"\btherefore\b",
        r"\bconsequently\b",
        r"\bleads to\b",
    ],
}

def detect_query_intent(query: str) -> List[str]:
    """
    Classify query into intents and map to collections.
    Always includes the paragraph collection.
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
        "definition": config.QDRANT_COLLECTION_NAME,
        "cause_effect": config.QDRANT_COLLECTION_NAME,
    }
    collections = set()
    for intent in detected_intents:
        collections.add(collection_map.get(intent, config.QDRANT_COLLECTION_NAME))
    # Always include paragraph collection
    collections.add(config.QDRANT_PARAGRAPH_COLLECTION)
    collections = list(collections)
    logger.info(f"[INTENT] Query intent(s): {detected_intents} → collections: {collections}")
    return collections

# ------------------------------------------------------------------------------
# Score normalization and RRF
# ------------------------------------------------------------------------------
def normalize_scores(candidates: List[Dict], score_key: str) -> List[Dict]:
    """Min‑max normalize scores in a list to [0,1]."""
    if not candidates:
        return candidates
    scores = [c.get(score_key, 0.0) for c in candidates]
    min_score = min(scores) if scores else 0.0
    max_score = max(scores) if scores else 1.0
    if max_score > min_score:
        for c, s in zip(candidates, scores):
            c[score_key + "_norm"] = (s - min_score) / (max_score - min_score)
    else:
        for c in candidates:
            c[score_key + "_norm"] = 0.0
    return candidates

def merge_candidates(
    dense_candidates: List[Dict],
    bm25_candidates: List[Dict],
    dense_weight: float = 0.5,
    bm25_weight: float = 0.5,
) -> List[Dict]:
    """
    Merge dense and BM25 candidates, deduplicate, and compute RRF.
    Weights should sum to 1.0 ideally.
    """
    # Normalize scores within each list
    dense_candidates = normalize_scores(dense_candidates, "dense_score")
    bm25_candidates = normalize_scores(bm25_candidates, "bm25_score")

    # Assign ranks based on normalized scores (higher is better)
    dense_candidates.sort(key=lambda x: x.get("dense_score_norm", 0.0), reverse=True)
    for idx, c in enumerate(dense_candidates):
        c["dense_rank"] = idx + 1
        c["dense_rrf"] = 1.0 / (60 + idx + 1)

    bm25_candidates.sort(key=lambda x: x.get("bm25_score_norm", 0.0), reverse=True)
    for idx, c in enumerate(bm25_candidates):
        c["bm25_rank"] = idx + 1
        c["bm25_rrf"] = 1.0 / (60 + idx + 1)

    # Merge with deduplication
    merged: Dict[Tuple[int, int, str], Dict] = {}
    for c in dense_candidates:
        key = (c.get("pipeline_id"), c.get("file_id"), c.get("chunk_id"))
        if key not in merged:
            merged[key] = dict(c)
            merged[key]["hybrid_score"] = c.get("dense_rrf", 0.0) * dense_weight
        else:
            merged[key]["hybrid_score"] += c.get("dense_rrf", 0.0) * dense_weight

    for c in bm25_candidates:
        key = (c.get("pipeline_id"), c.get("file_id"), c.get("chunk_id"))
        if key not in merged:
            merged[key] = dict(c)
            merged[key]["hybrid_score"] = c.get("bm25_rrf", 0.0) * bm25_weight
        else:
            merged[key]["hybrid_score"] += c.get("bm25_rrf", 0.0) * bm25_weight

    result_list = list(merged.values())
    result_list.sort(key=lambda x: x.get("hybrid_score", 0.0), reverse=True)
    return result_list

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
    Perform dense vector similarity search.
    Adds 'dense_score' and 'dense_rank'.
    """
    results = search_similar(
        collection_name=collection_name,
        query_vector=query_vector,
        top_k=top_k,
        filters=filters,
    )
    for r in results:
        r["dense_score"] = r.get("score", 0.0)
    results.sort(key=lambda x: x["dense_score"], reverse=True)
    for idx, r in enumerate(results):
        r["dense_rank"] = idx + 1
    return results

# ------------------------------------------------------------------------------
# BM25 retrieval wrapper
# ------------------------------------------------------------------------------
def retrieve_bm25_wrapper(pipeline_id: int, query: str, top_k: int) -> List[Dict]:
    """
    Wrapper around bm25_service.retrieve_bm25 to ensure bm25_score field.
    """
    results = retrieve_bm25(pipeline_id, query, top_k)
    for r in results:
        r["bm25_score"] = r.get("retrieval_score", r.get("score", 0.0))
    results.sort(key=lambda x: x.get("bm25_score", 0.0), reverse=True)
    for idx, r in enumerate(results):
        r["bm25_rank"] = idx + 1
    return results

# ------------------------------------------------------------------------------
# Importance boost (min‑max normalized, configurable weight) – used as fallback only
# ------------------------------------------------------------------------------
def apply_importance_boost(candidates: List[Dict]) -> List[Dict]:
    """
    Normalize importance_score and add to final_score with configurable weight.
    This is only used for fallback or logging; the reranker's order is primary.
    """
    if not candidates:
        return candidates
    scores = [c.get("importance_score", 0.0) for c in candidates]
    min_score = min(scores) if scores else 0.0
    max_score = max(scores) if scores else 1.0
    if max_score > min_score:
        for c in candidates:
            imp = c.get("importance_score", 0.0)
            c["importance_norm"] = (imp - min_score) / (max_score - min_score)
    else:
        for c in candidates:
            c["importance_norm"] = 0.0

    weight = getattr(config, "IMPORTANCE_BOOST_WEIGHT", 0.15)
    for c in candidates:
        c["final_score"] = c.get("score", 0.0) + c.get("importance_norm", 0.0) * weight
    return candidates

# ------------------------------------------------------------------------------
# Main retrieval‑and‑rerank orchestrator (correct order)
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
        4. Merge with RRF (weights from config)
        5. Cross‑encoder rerank on merged candidates
        6. Graph expansion on top reranked candidates
        7. Entity expansion on expanded set
        8. Final rerank (second pass) → output top_k
    """
    logger.info(f"[RETRIEVAL] Starting hybrid retrieval for query: '{query}'")

    # 1. Intent & collections
    collections = detect_query_intent(query)
    print(f"[RETRIEVAL] SEARCHING COLLECTIONS: {collections} for query: '{query}'", flush=True)

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
            bm25_res = retrieve_bm25_wrapper(pipeline_id, query, recall_limit)
            all_bm25_candidates.extend(bm25_res)
        except Exception as e:
            logger.warning(f"BM25 retrieval failed: {e}")

    if not all_dense_candidates and not all_bm25_candidates:
        return {"query": query, "results": [], "statistics": {}}

    # 4. Merge with RRF (weights from config)
    dense_weight = getattr(config, "RRF_DENSE_WEIGHT", 0.5)
    bm25_weight = getattr(config, "RRF_BM25_WEIGHT", 0.5)
    merged = merge_candidates(all_dense_candidates, all_bm25_candidates, dense_weight, bm25_weight)
    logger.info(f"[HYBRID] Merged {len(merged)} unique candidates")

    # 5. First cross‑encoder rerank on merged candidates
    candidates_for_rerank = merged[:recall_limit * 2]
    reranked_first = rerank(query, candidates_for_rerank, top_k=top_k * 2)  # get extra for expansion
    logger.info(f"[RERANK] Reranked to {len(reranked_first)} candidates")

    # 6. Graph expansion on top reranked candidates
    top_for_expansion = reranked_first[:top_k * 2] if reranked_first else []
    try:
        expanded = expand_graph_context(
            top_chunks=top_for_expansion,
            pipeline_id=pipeline_id,
            limit=top_k * 2,
        )
    except Exception as e:
        logger.warning(f"Graph expansion failed: {e}. Continuing without expansion.")
        expanded = top_for_expansion

    # Deduplicate expanded set
    seen: Set[Tuple[int, int, str]] = set()
    expanded_unique = []
    for c in expanded:
        key = (c.get("pipeline_id"), c.get("file_id"), c.get("chunk_id"))
        if key not in seen:
            seen.add(key)
            expanded_unique.append(c)
    expanded = expanded_unique
    graph_expansion_count = len(expanded) - len(top_for_expansion)
    logger.info(f"[GRAPH] Expanded to {len(expanded)} candidates (net new: {graph_expansion_count})")

    # 7. Entity expansion (same entity group) on expanded set
    before_entity_expansion = len(expanded)
    top_entity_groups = {r.get("entity_group") for r in expanded[:3] if r.get("entity_group") and r.get("entity_group") != "unknown"}
    if top_entity_groups:
        added_keys = {(r.get("pipeline_id"), r.get("file_id"), r.get("chunk_id")) for r in expanded}
        for cand in merged:
            if cand.get("entity_group") in top_entity_groups:
                key = (cand.get("pipeline_id"), cand.get("file_id"), cand.get("chunk_id"))
                if key not in added_keys:
                    expanded.append(cand)
                    added_keys.add(key)
        entity_expansion_count = len(expanded) - before_entity_expansion
        logger.info(f"[ENTITY] Expanded by {entity_expansion_count} candidates for groups: {top_entity_groups}")
    else:
        entity_expansion_count = 0

    # 8. Final rerank on the expanded set (second pass)
    if expanded:
        final_reranked = rerank(query, expanded, top_k=top_k)
    else:
        final_reranked = reranked_first[:top_k] if reranked_first else []

    # 9. Apply importance boost only for fallback (not for reordering)
    final_reranked = apply_importance_boost(final_reranked)
    # Keep order from reranker (which is already sorted by rerank score)
    # Do NOT re‑sort by final_score; reranker order is primary.

    # 10. Calibrate score for UI (use rerank score)
    for r in final_reranked:
        r["score"] = r.get("score", 0.0)  # reranker score

    # 11. Statistics
    statistics = {
        "intent": str(collections),
        "dense_candidates": len(all_dense_candidates),
        "bm25_candidates": len(all_bm25_candidates),
        "merged_candidates": len(merged),
        "reranked_before_expansion": len(reranked_first),
        "graph_expansion_count": graph_expansion_count,
        "entity_expansion_count": entity_expansion_count,
        "final_candidates": len(final_reranked),
        "top_k": top_k,
    }
    logger.info(f"[CONTEXT] Final context size: {len(final_reranked)}")

    logger.info(
        f"\n==================== RETRIEVAL FLOW EVALUATION ====================\n"
        f"Query: {query}\n"
        f"Statistics: {statistics}\n"
        f"Final chunks: {[c.get('chunk_id') for c in final_reranked]}\n"
        f"===================================================================\n"
    )

    return {
        "query": query,
        "results": final_reranked,
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