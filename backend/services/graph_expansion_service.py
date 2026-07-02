"""
graph_expansion_service.py — Graph-native context expansion for ScaleFlow.

Expands top-retrieved chunks using graph relations:
  - neighbors
  - semantic parent
  - semantic children
  - cross references
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pluggable chunk lookup — must be configured before use.
# ---------------------------------------------------------------------------
ChunkLookup = Callable[[int, int, str], Optional[Dict[str, Any]]]
_chunk_lookup: Optional[ChunkLookup] = None


def set_chunk_lookup(func: ChunkLookup) -> None:
    """Register a function to fetch a chunk by (pipeline_id, file_id, chunk_id)."""
    global _chunk_lookup
    _chunk_lookup = func


def get_chunk_by_id(pipeline_id: int, file_id: int, chunk_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a chunk dict from the configured lookup provider."""
    if _chunk_lookup is None:
        raise RuntimeError("Chunk lookup provider not configured. Call set_chunk_lookup() first.")
    return _chunk_lookup(pipeline_id, file_id, chunk_id)


# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------
DEFAULT_GRAPH_EXPANSION_DEPTH = 1
DEFAULT_GRAPH_EXPANSION_LIMIT = 50
MAX_NEIGHBORS_PER_CHUNK = 10
MAX_CHILDREN_PER_CHUNK = 10
MAX_CROSS_REFS_PER_CHUNK = 10

# Expansion weights
WEIGHT_ORIGINAL = 1.00
WEIGHT_NEIGHBOR = 0.80
WEIGHT_PARENT = 0.90
WEIGHT_CHILD = 0.75
WEIGHT_CROSSREF = 0.60


# ---------------------------------------------------------------------------
# Helper: collect related chunk IDs from a chunk dict
# ---------------------------------------------------------------------------
def _collect_ids(field: Any, max_items: int) -> List[str]:
    """Safely extract up to max_items string IDs from a field (list or dict of lists)."""
    ids: List[str] = []
    if isinstance(field, list):
        for item in field[:max_items]:
            if isinstance(item, str):
                ids.append(item)
    elif isinstance(field, dict):
        for v in field.values():
            if isinstance(v, list):
                for item in v:
                    if isinstance(item, str):
                        ids.append(item)
                        if len(ids) >= max_items:
                            return ids[:max_items]
    return ids[:max_items]


def collect_neighbors(
    chunk: Dict[str, Any], pipeline_id: int, file_id: int, limit: int = MAX_NEIGHBORS_PER_CHUNK
) -> List[Dict[str, Any]]:
    """Fetch up to `limit` neighbor chunks."""
    neighbors = _collect_ids(chunk.get("neighbors", []), limit)
    results: List[Dict[str, Any]] = []
    for nid in neighbors:
        node = get_chunk_by_id(pipeline_id, file_id, nid)
        if node:
            results.append(node)
        if len(results) >= limit:
            break
    return results


def collect_parents(
    chunk: Dict[str, Any], pipeline_id: int, file_id: int, limit: int = 1
) -> List[Dict[str, Any]]:
    """Fetch semantic parent (single chunk)."""
    parent_id = chunk.get("semantic_parent")
    if parent_id and isinstance(parent_id, str):
        node = get_chunk_by_id(pipeline_id, file_id, parent_id)
        if node:
            return [node]
    return []


def collect_children(
    chunk: Dict[str, Any], pipeline_id: int, file_id: int, limit: int = MAX_CHILDREN_PER_CHUNK
) -> List[Dict[str, Any]]:
    """Fetch up to `limit` semantic children."""
    children = _collect_ids(chunk.get("semantic_children", []), limit)
    results: List[Dict[str, Any]] = []
    for cid in children:
        node = get_chunk_by_id(pipeline_id, file_id, cid)
        if node:
            results.append(node)
        if len(results) >= limit:
            break
    return results


def collect_cross_refs(
    chunk: Dict[str, Any], pipeline_id: int, file_id: int, limit: int = MAX_CROSS_REFS_PER_CHUNK
) -> List[Dict[str, Any]]:
    """Fetch up to `limit` cross‑referenced chunks (tables, figures, etc.)."""
    cross_refs = _collect_ids(chunk.get("cross_refs", []), limit)
    results: List[Dict[str, Any]] = []
    for rid in cross_refs:
        node = get_chunk_by_id(pipeline_id, file_id, rid)
        if node:
            results.append(node)
        if len(results) >= limit:
            break
    return results


# ---------------------------------------------------------------------------
# Scoring and deduplication
# ---------------------------------------------------------------------------
def score_expansion(
    chunks: List[Dict[str, Any]],
    original_score: float,
    weight: float,
    relation: str,
    is_original: bool = False,
) -> List[Dict[str, Any]]:
    """
    Attach graph‑expansion metadata to a list of raw chunks.
    Returns the same objects enriched with scoring fields.
    """
    for c in chunks:
        c["graph_expansion"] = not is_original
        c["graph_relation"] = relation if not is_original else "original"
        c["graph_score"] = weight
        if "retrieval_score" not in c:
            c["retrieval_score"] = original_score
    return chunks


def deduplicate_expansion(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Deduplicate by (pipeline_id, file_id, chunk_id), keeping the highest graph_score.
    """
    seen: Dict[Tuple[int, int, str], Dict[str, Any]] = {}
    for entry in entries:
        pid = entry.get("pipeline_id")
        fid = entry.get("file_id")
        cid = entry.get("chunk_id")
        if pid is None or fid is None or cid is None:
            continue
        key = (int(pid), int(fid), str(cid))
        if key not in seen:
            seen[key] = entry
        else:
            existing_score = seen[key].get("graph_score", 0.0)
            current_score = entry.get("graph_score", 0.0)
            if current_score > existing_score:
                seen[key] = entry
    return list(seen.values())


# ---------------------------------------------------------------------------
# Single chunk expansion
# ---------------------------------------------------------------------------
def expand_single_chunk(
    chunk: Dict[str, Any],
    pipeline_id: int,
    depth: int = 1,
    limit_per_type: int = 10,
    visited: Optional[Set[Tuple[int, int, str]]] = None,
) -> List[Dict[str, Any]]:
    """
    Expand one chunk: collect neighbors, parent, children, cross‑refs.
    The returned list includes the original chunk (scored as original) and the
    newly fetched chunks with appropriate graph scores.

    Args:
        chunk: the original chunk dict. Must contain 'chunk_id' and 'file_id'.
        pipeline_id: owning pipeline.
        depth: expansion depth (currently only depth=1 is implemented).
        limit_per_type: max items per relation type.
        visited: set of (pipeline_id, file_id, chunk_id) already visited.

    Returns:
        list of chunk dicts enriched with scoring and expansion metadata.
    """
    if visited is None:
        visited = set()

    file_id = chunk.get("file_id")
    if file_id is None:
        logger.warning("Chunk missing file_id, skipping expansion")
        return [chunk]

    original_id = str(chunk.get("chunk_id", ""))
    visited_key = (pipeline_id, int(file_id), original_id)
    visited.add(visited_key)

    if depth > 1:
        logger.warning("Multi-hop graph expansion (depth > 1) is not yet implemented. Using depth=1.")
        depth = 1

    result: List[Dict[str, Any]] = []
    # Add the original chunk with full score
    scored_original = score_expansion(
        [chunk], chunk.get("retrieval_score", 1.0), WEIGHT_ORIGINAL, "original", is_original=True
    )
    result.extend(scored_original)

    # 1. neighbors
    neighbors = collect_neighbors(chunk, pipeline_id, file_id, limit_per_type)
    for nb in neighbors:
        nb_id = str(nb.get("chunk_id", ""))
        nb_fid = nb.get("file_id", file_id)  # inherit if missing
        nb_key = (pipeline_id, int(nb_fid), nb_id)
        if nb_key not in visited:
            visited.add(nb_key)
            result.extend(
                score_expansion([nb], chunk.get("retrieval_score", 1.0), WEIGHT_NEIGHBOR, "neighbor")
            )

    # 2. semantic parent
    parents = collect_parents(chunk, pipeline_id, file_id)
    for p in parents:
        p_id = str(p.get("chunk_id", ""))
        p_fid = p.get("file_id", file_id)
        p_key = (pipeline_id, int(p_fid), p_id)
        if p_key not in visited:
            visited.add(p_key)
            result.extend(
                score_expansion([p], chunk.get("retrieval_score", 1.0), WEIGHT_PARENT, "parent")
            )

    # 3. semantic children
    children = collect_children(chunk, pipeline_id, file_id, limit_per_type)
    for child in children:
        c_id = str(child.get("chunk_id", ""))
        c_fid = child.get("file_id", file_id)
        c_key = (pipeline_id, int(c_fid), c_id)
        if c_key not in visited:
            visited.add(c_key)
            result.extend(
                score_expansion([child], chunk.get("retrieval_score", 1.0), WEIGHT_CHILD, "child")
            )

    # 4. cross references
    cross = collect_cross_refs(chunk, pipeline_id, file_id, limit_per_type)
    for x in cross:
        x_id = str(x.get("chunk_id", ""))
        x_fid = x.get("file_id", file_id)
        x_key = (pipeline_id, int(x_fid), x_id)
        if x_key not in visited:
            visited.add(x_key)
            result.extend(
                score_expansion([x], chunk.get("retrieval_score", 1.0), WEIGHT_CROSSREF, "cross_ref")
            )

    return result


# ---------------------------------------------------------------------------
# Main expansion entry point
# ---------------------------------------------------------------------------
def expand_graph_context(
    top_chunks: List[Dict[str, Any]],
    pipeline_id: int,
    expansion_depth: int = DEFAULT_GRAPH_EXPANSION_DEPTH,
    limit: int = DEFAULT_GRAPH_EXPANSION_LIMIT,
) -> List[Dict[str, Any]]:
    """
    Expand a list of top‑retrieved chunks using their graph relations.

    Args:
        top_chunks: list of chunk dicts from dense/BM25 retrieval.
        pipeline_id: ID of the pipeline.
        expansion_depth: how many hops to expand (default 1).
        limit: maximum number of chunks to return after expansion.

    Returns:
        deduplicated list of enriched chunk dicts, with graph expansion metadata.
    """
    if not top_chunks:
        return []

    start = time.perf_counter()
    all_entries: List[Dict[str, Any]] = []
    visited: Set[Tuple[int, int, str]] = set()

    # A reasonable per‑type limit that doesn't starve categories
    limit_per_type = min(MAX_NEIGHBORS_PER_CHUNK, max(3, limit // 10))

    for chunk in top_chunks:
        # Ensure pipeline_id is set
        chunk.setdefault("pipeline_id", pipeline_id)
        # Ensure file_id is set; if not present, we cannot expand reliably but we can try.
        if "file_id" not in chunk:
            logger.warning(f"Chunk {chunk.get('chunk_id')} has no file_id; expansion skipped.")
            chunk["graph_expansion"] = False
            chunk["graph_score"] = WEIGHT_ORIGINAL
            chunk["graph_relation"] = "original"
            chunk.setdefault("retrieval_score", 1.0)
            all_entries.append(chunk)
            continue

        try:
            expanded = expand_single_chunk(
                chunk,
                pipeline_id=pipeline_id,
                depth=expansion_depth,
                limit_per_type=limit_per_type,
                visited=visited,
            )
            all_entries.extend(expanded)
        except Exception as e:
            logger.warning(f"Expansion failed for chunk {chunk.get('chunk_id')}: {e}")
            # Ensure consistent schema on fallback
            chunk["graph_expansion"] = False
            chunk["graph_score"] = WEIGHT_ORIGINAL
            chunk["graph_relation"] = "original"
            chunk.setdefault("retrieval_score", 1.0)
            all_entries.append(chunk)

    deduped = deduplicate_expansion(all_entries)
    if len(deduped) > limit:
        deduped = deduped[:limit]

    elapsed = time.perf_counter() - start
    logger.info(
        f"Graph expansion: {len(top_chunks)} seeds → {len(all_entries)} candidates → "
        f"{len(deduped)} final ({elapsed*1000:.1f} ms)"
    )
    return deduped


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------
__all__ = [
    "set_chunk_lookup",
    "expand_graph_context",
    "expand_single_chunk",
    "score_expansion",
    "deduplicate_expansion",
    "collect_neighbors",
    "collect_parents",
    "collect_children",
    "collect_cross_refs",
]