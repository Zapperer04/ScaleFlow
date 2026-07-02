import os
import sys
import re
import logging
import tempfile
from typing import List, Dict, Any, Optional

# Adjust path to find config and services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from services.vector_store import search_similar, search_keyword, get_client

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# Whoosh-based BM25 (optional, fallback to keyword search if not installed)
# ------------------------------------------------------------------------------
try:
    from whoosh import index as whoosh_index
    from whoosh.fields import Schema, TEXT, ID, NUMERIC
    from whoosh.qparser import QueryParser, MultifieldParser
    from whoosh.query import And, Term
    from whoosh.writing import AsyncWriter
    WHOOSH_AVAILABLE = True
except ImportError:
    WHOOSH_AVAILABLE = False

# Global index storage (lazy built per collection)
_whoosh_indexes = {}

def _get_whoosh_index_dir(collection_name: str) -> str:
    """Return a persistent directory for the Whoosh index of a collection."""
    base_dir = os.path.join(tempfile.gettempdir(), "scaleflow_whoosh")
    os.makedirs(base_dir, exist_ok=True)
    return os.path.join(base_dir, collection_name)

def _build_whoosh_index(collection_name: str) -> bool:
    """
    Build (or rebuild) a Whoosh index from all chunks in a Qdrant collection.
    Uses Qdrant's scroll to fetch all payloads. This can be slow for large collections.
    """
    if not WHOOSH_AVAILABLE:
        logger.warning("Whoosh not installed, cannot build BM25 index")
        return False

    try:
        client = get_client()
        schema = Schema(
            chunk_id=ID(stored=True, unique=True),
            bm25_text=TEXT(stored=True, analyzer=whoosh_analysis.StandardAnalyzer()),
            pipeline_id=NUMERIC(stored=True),   # for filtering
            file_id=NUMERIC(stored=True)
        )
        index_dir = _get_whoosh_index_dir(collection_name)
        # Remove old index if exists
        if whoosh_index.exists_in(index_dir):
            ix = whoosh_index.open_dir(index_dir)
        else:
            os.makedirs(index_dir, exist_ok=True)
            ix = whoosh_index.create_in(index_dir, schema)
        
        writer = ix.writer()
        offset = 0
        batch_size = 100
        while True:
            points, next_offset = client.scroll(
                collection_name=collection_name,
                limit=batch_size,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )
            if not points:
                break
            for point in points:
                payload = point.payload
                if not payload.get("bm25_text"):
                    continue
                writer.update_document(
                    chunk_id=str(payload.get("chunk_id") or payload.get("chunk_index")),
                    bm25_text=payload["bm25_text"],
                    pipeline_id=payload.get("pipeline_id"),
                    file_id=payload.get("file_id")
                )
            offset = next_offset if next_offset else offset + batch_size
            # Safety break if same offset (but Qdrant scroll with offset should advance)
            if offset >= 100000:  # artificial limit for now
                break
        writer.commit()
        _whoosh_indexes[collection_name] = ix
        logger.info(f"Whoosh index built for collection '{collection_name}' with {ix.doc_count()} documents")
        return True
    except Exception as e:
        logger.error(f"Failed to build Whoosh index for {collection_name}: {e}")
        return False

def _get_whoosh_index(collection_name: str):
    """Return the Whoosh index, building it if necessary."""
    if collection_name not in _whoosh_indexes:
        index_dir = _get_whoosh_index_dir(collection_name)
        if whoosh_index.exists_in(index_dir):
            _whoosh_indexes[collection_name] = whoosh_index.open_dir(index_dir)
        else:
            success = _build_whoosh_index(collection_name)
            if not success:
                return None
    return _whoosh_indexes.get(collection_name)

# ------------------------------------------------------------------------------
# Query intent detection (unchanged from before)
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

def detect_query_intent(query: str) -> list[str]:
    """Classify query into intents and map to collections."""
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
    }
    collections = list(set(collection_map.get(i, config.QDRANT_COLLECTION_NAME) for i in detected_intents))
    logger.info(f"[INTENT] Query intent(s): {detected_intents} → collections: {collections}")
    return collections


# ------------------------------------------------------------------------------
# BM25 retrieval (true Whoosh-based, fallback to keyword search)
# ------------------------------------------------------------------------------
def retrieve_bm25(query: str, collection_name: str, top_k: int = 30, filters: Optional[Dict] = None) -> List[Dict]:
    """
    Retrieve chunks using BM25 scoring (via Whoosh).
    Falls back to Qdrant keyword search if Whoosh unavailable or index missing.
    """
    if not query:
        return []
    if not WHOOSH_AVAILABLE:
        logger.warning("[BM25] Whoosh not installed, falling back to keyword search")
        results = search_keyword(collection_name, query, top_k, filters)
        for r in results:
            r["bm25_score"] = r.get("score", 0.5)
        return results

    ix = _get_whoosh_index(collection_name)
    if ix is None:
        logger.warning(f"[BM25] No Whoosh index for {collection_name}, falling back to keyword search")
        results = search_keyword(collection_name, query, top_k, filters)
        for r in results:
            r["bm25_score"] = r.get("score", 0.5)
        return results

    # Build Whoosh query with filters
    qp = QueryParser("bm25_text", schema=ix.schema)
    try:
        user_query = qp.parse(query)
    except Exception as e:
        logger.error(f"[BM25] Query parsing error: {e}")
        return []

    # Apply filters as additional terms (AND)
    if filters:
        for key, val in filters.items():
            if key in ("pipeline_id", "file_id"):
                try:
                    val = int(val)
                except (ValueError, TypeError):
                    continue
                user_query = And([user_query, Term(key, val)])

    with ix.searcher() as searcher:
        results = searcher.search(user_query, limit=top_k)
        scored_chunks = []
        for hit in results:
            # We only stored chunk_id and text; we need full payloads from Qdrant.
            # So we'll fetch by chunk_id from Qdrant (or use in-memory store later).
            # For now, return minimal info with BM25 score.
            scored_chunks.append({
                "chunk_id": hit["chunk_id"],
                "bm25_text": hit["bm25_text"],
                "bm25_score": hit.score,  # Whoosh score
                # Missing other fields like section, entities, etc. – we'll merge later.
            })
        return scored_chunks


# ------------------------------------------------------------------------------
# Dense retrieval wrapper (unchanged)
# ------------------------------------------------------------------------------
def retrieve_dense(query_vector: list, collection_name: str, top_k: int = 30, filters: Optional[Dict] = None) -> List[Dict]:
    """Perform dense vector similarity search."""
    results = search_similar(
        collection_name=collection_name,
        query_vector=query_vector,
        top_k=top_k,
        filters=filters
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
    """Merge and deduplicate by chunk_id, compute hybrid score."""
    merged = {}
    for cand in dense_candidates:
        cid = cand.get("chunk_id") or cand.get("chunk_index")
        if cid not in merged:
            merged[cid] = dict(cand)
            merged[cid]["hybrid_score"] = cand.get("dense_score", 0.0) * dense_weight
        else:
            merged[cid]["hybrid_score"] += cand.get("dense_score", 0.0) * dense_weight
    for cand in bm25_candidates:
        cid = cand.get("chunk_id") or cand.get("chunk_index")
        if cid not in merged:
            merged[cid] = dict(cand)
            merged[cid]["hybrid_score"] = cand.get("bm25_score", 0.0) * bm25_weight
        else:
            merged[cid]["hybrid_score"] += cand.get("bm25_score", 0.0) * bm25_weight
    return list(merged.values())


# ------------------------------------------------------------------------------
# Graph expansion & scoring
# ------------------------------------------------------------------------------
def expand_graph_context(candidates: List[Dict], expansion_depth: int = 1) -> List[Dict]:
    """Boost scores based on graph connectivity (neighbors, cross_refs)."""
    for cand in candidates:
        neighbours = cand.get("neighbors", [])
        cross_refs = cand.get("cross_refs", {})
        if isinstance(cross_refs, dict):
            cross_ref_count = sum(len(v) for v in cross_refs.values()) if cross_refs else 0
        else:
            cross_ref_count = len(cross_refs) if cross_refs else 0
        graph_expansion_score = (len(neighbours) * 0.01) + (cross_ref_count * 0.02)
        cand["graph_expansion_score"] = graph_expansion_score
    return candidates


# ------------------------------------------------------------------------------
# Importance boost
# ------------------------------------------------------------------------------
def apply_importance_boost(candidates: List[Dict]) -> List[Dict]:
    """Add importance_score * 0.15 to hybrid score."""
    for cand in candidates:
        importance = cand.get("importance_score", 0.0)
        cand["final_score"] = cand.get("hybrid_score", 0.0) + importance * 0.15 + cand.get("graph_expansion_score", 0.0)
    return candidates


# ------------------------------------------------------------------------------
# Main retrieval-and-rerank pipeline
# ------------------------------------------------------------------------------
def retrieve_and_rerank(
    query_vector: list,
    pipeline_id: int = None,
    top_k: int = 5,
    query: str = ""
) -> dict:
    """
    Graph-native hybrid retrieval pipeline.
    """
    logger.info(f"[RETRIEVAL] Starting hybrid retrieval for query: '{query}'")

    # 1. Intent classification & collection selection
    collections = detect_query_intent(query)
    print(f"[RETRIEVAL] SEARCHING COLLECTIONS: {collections} for query: '{query}'", flush=True)

    # Only filter by pipeline_id when explicitly provided
    filters = {"pipeline_id": pipeline_id} if pipeline_id is not None else None

    # High recall limits
    recall_limit = max(top_k * 5, 30)

    all_dense_candidates = []
    all_bm25_candidates = []

    # 2. Retrieve dense and BM25 from each collection
    for coll in collections:
        # Dense
        dense_res = retrieve_dense(query_vector, coll, top_k=recall_limit, filters=filters)
        all_dense_candidates.extend(dense_res)
        # BM25
        if query:
            bm25_res = retrieve_bm25(query, coll, top_k=recall_limit, filters=filters)
            all_bm25_candidates.extend(bm25_res)

    if not all_dense_candidates and not all_bm25_candidates:
        return {"query": query, "results": [], "statistics": {}}

    # 3. Merge candidates with hybrid scoring
    merged = merge_candidates(all_dense_candidates, all_bm25_candidates)
    logger.info(f"[HYBRID] Merged {len(merged)} unique candidates")

    # 4. Graph expansion scoring
    merged = expand_graph_context(merged)
    logger.info(f"[GRAPH] Applied graph expansion scores")

    # 5. Importance boost
    merged = apply_importance_boost(merged)
    logger.info(f"[SCORE] Applied importance boost")

    # 6. Rerank with cross-encoder
    from services.reranker_service import rerank
    merged.sort(key=lambda x: x.get("final_score", 0.0), reverse=True)
    candidates_for_rerank = merged[:max(recall_limit, top_k * 3)]
    reranked = rerank(query, candidates_for_rerank, top_k=top_k)
    logger.info(f"[RERANK] Reranked down to {len(reranked)} results")

    # 7. Assemble context
    statistics = {
        "intent": str(collections),
        "dense_candidates": len(all_dense_candidates),
        "bm25_candidates": len(all_bm25_candidates),
        "graph_expansions": 0,
        "final_context_size": len(reranked),
    }
    logger.info(f"[CONTEXT] Final context size: {len(reranked)}")

    return {
        "query": query,
        "results": reranked,
        "statistics": statistics,
    }


# ------------------------------------------------------------------------------
# Backward-compatible wrapper
# ------------------------------------------------------------------------------
def retrieve_context(query_vector: list, pipeline_id: int, top_k: int = None, query: str = "") -> dict:
    """Legacy wrapper."""
    if top_k is None:
        top_k = config.DEFAULT_RETRIEVAL_TOP_K
    return retrieve_and_rerank(query_vector=query_vector, pipeline_id=pipeline_id, top_k=top_k, query=query)


# ------------------------------------------------------------------------------
# Module exports
# ------------------------------------------------------------------------------
__all__ = [
    "retrieve_context",
    "retrieve_and_rerank",
    "detect_query_intent",
    "retrieve_bm25",
    "retrieve_dense",
    "merge_candidates",
    "expand_graph_context",
    "apply_importance_boost",
]