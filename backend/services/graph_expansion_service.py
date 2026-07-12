"""
graph_expansion_service.py — Graph-native context expansion for ScaleFlow.

Expands top-retrieved chunks using graph relations:
  - neighbors
  - semantic parent
  - semantic children
  - cross references

Now with proper multi-hop BFS, batch fetching, and (file_id, chunk_id) keys.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pluggable chunk lookup — must be configured before use.
# ---------------------------------------------------------------------------
BatchChunkLookup = Callable[
    [int, List[Tuple[int, str]]],
    Dict[Tuple[int, str], Dict[str, Any]]
]

_batch_chunk_lookup: Optional[BatchChunkLookup] = None

def set_batch_chunk_lookup(func: BatchChunkLookup) -> None:
    """
    Register a function to fetch multiple chunks by (file_id, chunk_id) pairs.
    Returns a dict mapping (file_id, chunk_id) -> chunk dict.
    """
    global _batch_chunk_lookup
    _batch_chunk_lookup = func

def get_chunks_batch(pipeline_id: int, requests: List[Tuple[int, str]]) -> Dict[Tuple[int, str], Dict[str, Any]]:
    """Fetch multiple chunks in one batch."""
    if _batch_chunk_lookup is None:
        raise RuntimeError("Batch chunk lookup provider not configured. Call set_batch_chunk_lookup() first.")
    return _batch_chunk_lookup(pipeline_id, requests)

# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------
DEFAULT_GRAPH_EXPANSION_DEPTH = 1
DEFAULT_GRAPH_EXPANSION_LIMIT = 50
MAX_NEIGHBORS_PER_CHUNK = 10
MAX_CHILDREN_PER_CHUNK = 10
MAX_CROSS_REFS_PER_CHUNK = 10

# Expansion weights (base scores, multiplied by original retrieval score)
WEIGHT_ORIGINAL = 1.00
WEIGHT_NEIGHBOR = 0.80
WEIGHT_PARENT = 0.90
WEIGHT_CHILD = 0.75
WEIGHT_CROSSREF = 0.60
DECAY_PER_HOP = 0.7   # multiplier for each additional hop beyond the first

# ---------------------------------------------------------------------------
# Helper: collect related chunk IDs from a chunk dict
# ---------------------------------------------------------------------------
def _collect_ids(field: Any, max_items: int) -> List[Tuple[int, str]]:
    """
    Extract up to max_items (file_id, chunk_id) pairs from a field.
    Returns list of (file_id, chunk_id) tuples.
    If file_id is missing, it will be None (caller will fill with parent file_id).
    """
    ids: List[Tuple[int, str]] = []
    if isinstance(field, list):
        for item in field[:max_items]:
            if isinstance(item, str):
                # We'll use None as placeholder; caller will fill with parent file_id
                ids.append((None, item))
            elif isinstance(item, dict):
                fid = item.get("file_id")
                cid = item.get("chunk_id")
                if cid and isinstance(cid, str):
                    ids.append((fid, cid))
    elif isinstance(field, dict):
        for v in field.values():
            if isinstance(v, list):
                for item in v:
                    if isinstance(item, str):
                        ids.append((None, item))
                    elif isinstance(item, dict):
                        fid = item.get("file_id")
                        cid = item.get("chunk_id")
                        if cid and isinstance(cid, str):
                            ids.append((fid, cid))
                    if len(ids) >= max_items:
                        return ids[:max_items]
    return ids[:max_items]

# ---------------------------------------------------------------------------
# Main expansion entry point (with proper BFS)
# ---------------------------------------------------------------------------
def expand_graph_context(
    top_chunks: List[Dict[str, Any]],
    pipeline_id: int,
    expansion_depth: int = DEFAULT_GRAPH_EXPANSION_DEPTH,
    limit: int = DEFAULT_GRAPH_EXPANSION_LIMIT,
) -> List[Dict[str, Any]]:
    """
    Expand a list of top‑retrieved chunks using their graph relations, with batched fetching.

    Uses iterative BFS up to `expansion_depth` hops.
    """
    if not top_chunks:
        return []

    if expansion_depth <= 0:
        return top_chunks[:limit]

    if _batch_chunk_lookup is None:
        raise RuntimeError("Batch chunk lookup provider not configured.")

    start = time.perf_counter()

    # We'll collect all expanded entries here
    all_entries: List[Dict[str, Any]] = []

    # Track visited (file_id, chunk_id) to avoid duplicate requests
    visited: Set[Tuple[int, str]] = set()

    # Layer 0: seeds
    # Also add seeds as original entries
    current_layer = top_chunks[:]  # list of dicts
    for seed in current_layer:
        cid = seed.get("chunk_id")
        fid = seed.get("file_id")
        if cid and fid is not None:
            fid = int(fid)
            key = (fid, cid)
            if key not in visited:
                visited.add(key)
                entry = dict(seed)
                entry["graph_score"] = seed.get("retrieval_score", 1.0) * WEIGHT_ORIGINAL
                entry["graph_hop"] = 0
                entry["graph_relations"] = ["original"]
                entry["retrieval_score"] = seed.get("retrieval_score", 1.0)
                all_entries.append(entry)

    for hop in range(1, expansion_depth + 1):
        # Collect all relation IDs from the current layer
        layer_requests = []
        for chunk in current_layer:
            file_id = chunk.get("file_id")
            if file_id is None:
                continue
            file_id = int(file_id)
            chunk_id = chunk.get("chunk_id")
            if not chunk_id:
                continue
            seed_score = chunk.get("retrieval_score", 1.0)
            seed_file_id = chunk.get("graph_seed_file_id", file_id)
            seed_chunk_id = chunk.get("graph_seed_chunk_id", chunk_id)

            # Neighbors
            neighbor_ids = _collect_ids(chunk.get("neighbors", []), MAX_NEIGHBORS_PER_CHUNK)
            for fid, cid in neighbor_ids:
                if fid is None:
                    fid = file_id
                else:
                    fid = int(fid)
                key = (fid, cid)
                if key not in visited:
                    visited.add(key)
                    layer_requests.append({
                        "file_id": fid,
                        "chunk_id": cid,
                        "relation": "neighbor",
                        "weight": WEIGHT_NEIGHBOR,
                        "original_score": seed_score,
                        "seed_file_id": seed_file_id,
                        "seed_chunk_id": seed_chunk_id,
                    })

            # Parent
            parent_id = chunk.get("semantic_parent")
            if parent_id and isinstance(parent_id, str):
                fid = file_id
                key = (fid, parent_id)
                if key not in visited:
                    visited.add(key)
                    layer_requests.append({
                        "file_id": fid,
                        "chunk_id": parent_id,
                        "relation": "parent",
                        "weight": WEIGHT_PARENT,
                        "original_score": seed_score,
                        "seed_file_id": seed_file_id,
                        "seed_chunk_id": seed_chunk_id,
                    })

            # Children
            child_ids = _collect_ids(chunk.get("semantic_children", []), MAX_CHILDREN_PER_CHUNK)
            for fid, cid in child_ids:
                if fid is None:
                    fid = file_id
                else:
                    fid = int(fid)
                key = (fid, cid)
                if key not in visited:
                    visited.add(key)
                    layer_requests.append({
                        "file_id": fid,
                        "chunk_id": cid,
                        "relation": "child",
                        "weight": WEIGHT_CHILD,
                        "original_score": seed_score,
                        "seed_file_id": seed_file_id,
                        "seed_chunk_id": seed_chunk_id,
                    })

            # Cross-references
            cross_ids = _collect_ids(chunk.get("cross_refs", []), MAX_CROSS_REFS_PER_CHUNK)
            for fid, cid in cross_ids:
                if fid is None:
                    fid = file_id
                else:
                    fid = int(fid)
                key = (fid, cid)
                if key not in visited:
                    visited.add(key)
                    layer_requests.append({
                        "file_id": fid,
                        "chunk_id": cid,
                        "relation": "cross_ref",
                        "weight": WEIGHT_CROSSREF,
                        "original_score": seed_score,
                        "seed_file_id": seed_file_id,
                        "seed_chunk_id": seed_chunk_id,
                    })

        if not layer_requests:
            break

        # Batch fetch all chunks in this layer
        fetch_tuples = [(req["file_id"], req["chunk_id"]) for req in layer_requests]
        fetched = get_chunks_batch(pipeline_id, fetch_tuples)  # returns dict (file_id, chunk_id) -> chunk

        # Build next layer and add entries
        next_layer = []
        for req in layer_requests:
            chunk = fetched.get((req["file_id"], req["chunk_id"]))
            if not chunk:
                continue

            # Compute graph score with decay
            decay = DECAY_PER_HOP ** (hop - 1)
            graph_score = req["original_score"] * req["weight"] * decay

            # Create entry
            entry = dict(chunk)
            entry["graph_score"] = graph_score
            entry["graph_hop"] = hop
            entry["graph_relations"] = [req["relation"]]
            entry["retrieval_score"] = req["original_score"]
            entry["graph_seed_file_id"] = req["seed_file_id"]
            entry["graph_seed_chunk_id"] = req["seed_chunk_id"]
            all_entries.append(entry)

            # Add to next layer for further expansion
            if hop < expansion_depth:
                next_layer.append(entry)

        current_layer = next_layer
        if not current_layer:
            break

    # Deduplicate by (file_id, chunk_id), merging graph_relations
    dedup_map: Dict[Tuple[int, str], Dict[str, Any]] = {}
    for entry in all_entries:
        fid = entry.get("file_id")
        cid = entry.get("chunk_id")
        if fid is None or cid is None:
            continue
        fid = int(fid)
        key = (fid, cid)
        existing = dedup_map.get(key)
        if existing is None or entry.get("graph_score", 0.0) > existing.get("graph_score", 0.0):
            dedup_map[key] = entry
        else:
            # Merge relations
            if "graph_relations" in existing and "graph_relations" in entry:
                existing["graph_relations"] = list(set(existing["graph_relations"] + entry["graph_relations"]))

    # Sort by graph_score and truncate
    deduped = list(dedup_map.values())
    deduped.sort(key=lambda x: x.get("graph_score", 0.0), reverse=True)
    if len(deduped) > limit:
        deduped = deduped[:limit]

    # Clean up: remove old graph_relation field if present
    for d in deduped:
        if "graph_relation" in d:
            del d["graph_relation"]
        # Ensure graph_relations is always a list
        if "graph_relations" not in d or not isinstance(d["graph_relations"], list):
            d["graph_relations"] = []

    # Telemetry
    elapsed = time.perf_counter() - start
    relation_counts = defaultdict(int)
    for entry in deduped:
        for rel in entry.get("graph_relations", []):
            relation_counts[rel] += 1

    logger.info(
        f"Graph expansion: {len(top_chunks)} seeds, depth={expansion_depth}, "
        f"{len(all_entries)} candidates → {len(deduped)} final "
        f"({elapsed*1000:.1f} ms). Relations: {dict(relation_counts)}"
    )

    return deduped

# ---------------------------------------------------------------------------
# Backward‑compatible single‑chunk expansion (uses the main function)
# ---------------------------------------------------------------------------
def expand_single_chunk(
    chunk: Dict[str, Any],
    pipeline_id: int,
    depth: int = 1,
    limit_per_type: int = 10,
    visited: Optional[Set[Tuple[int, int, str]]] = None,
) -> List[Dict[str, Any]]:
    """
    Legacy function – kept for backward compatibility.
    """
    # Ignore visited (we'll use the batch version)
    return expand_graph_context([chunk], pipeline_id, expansion_depth=depth, limit=limit_per_type * 4)

# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------
__all__ = [
    "set_batch_chunk_lookup",
    "expand_graph_context",
    "expand_single_chunk",
]"""
graph_expansion_service.py — Graph-native context expansion for ScaleFlow.

Expands top-retrieved chunks using graph relations:
  - neighbors
  - semantic parent
  - semantic children
  - cross references

Now with proper multi-hop BFS, batch fetching, and (file_id, chunk_id) keys.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pluggable chunk lookup — must be configured before use.
# ---------------------------------------------------------------------------
BatchChunkLookup = Callable[
    [int, List[Tuple[int, str]]],
    Dict[Tuple[int, str], Dict[str, Any]]
]

_batch_chunk_lookup: Optional[BatchChunkLookup] = None

def set_batch_chunk_lookup(func: BatchChunkLookup) -> None:
    """
    Register a function to fetch multiple chunks by (file_id, chunk_id) pairs.
    Returns a dict mapping (file_id, chunk_id) -> chunk dict.
    """
    global _batch_chunk_lookup
    _batch_chunk_lookup = func

def get_chunks_batch(pipeline_id: int, requests: List[Tuple[int, str]]) -> Dict[Tuple[int, str], Dict[str, Any]]:
    """Fetch multiple chunks in one batch."""
    if _batch_chunk_lookup is None:
        raise RuntimeError("Batch chunk lookup provider not configured. Call set_batch_chunk_lookup() first.")
    return _batch_chunk_lookup(pipeline_id, requests)

# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------
DEFAULT_GRAPH_EXPANSION_DEPTH = 1
DEFAULT_GRAPH_EXPANSION_LIMIT = 50
MAX_NEIGHBORS_PER_CHUNK = 10
MAX_CHILDREN_PER_CHUNK = 10
MAX_CROSS_REFS_PER_CHUNK = 10

# Expansion weights (base scores, multiplied by original retrieval score)
WEIGHT_ORIGINAL = 1.00
WEIGHT_NEIGHBOR = 0.80
WEIGHT_PARENT = 0.90
WEIGHT_CHILD = 0.75
WEIGHT_CROSSREF = 0.60
DECAY_PER_HOP = 0.7   # multiplier for each additional hop beyond the first

# ---------------------------------------------------------------------------
# Helper: collect related chunk IDs from a chunk dict
# ---------------------------------------------------------------------------
def _collect_ids(field: Any, max_items: int) -> List[Tuple[int, str]]:
    """
    Extract up to max_items (file_id, chunk_id) pairs from a field.
    Returns list of (file_id, chunk_id) tuples.
    If file_id is missing, it will be None (caller will fill with parent file_id).
    """
    ids: List[Tuple[int, str]] = []
    if isinstance(field, list):
        for item in field[:max_items]:
            if isinstance(item, str):
                # We'll use None as placeholder; caller will fill with parent file_id
                ids.append((None, item))
            elif isinstance(item, dict):
                fid = item.get("file_id")
                cid = item.get("chunk_id")
                if cid and isinstance(cid, str):
                    ids.append((fid, cid))
    elif isinstance(field, dict):
        for v in field.values():
            if isinstance(v, list):
                for item in v:
                    if isinstance(item, str):
                        ids.append((None, item))
                    elif isinstance(item, dict):
                        fid = item.get("file_id")
                        cid = item.get("chunk_id")
                        if cid and isinstance(cid, str):
                            ids.append((fid, cid))
                    if len(ids) >= max_items:
                        return ids[:max_items]
    return ids[:max_items]

# ---------------------------------------------------------------------------
# Main expansion entry point (with proper BFS)
# ---------------------------------------------------------------------------
def expand_graph_context(
    top_chunks: List[Dict[str, Any]],
    pipeline_id: int,
    expansion_depth: int = DEFAULT_GRAPH_EXPANSION_DEPTH,
    limit: int = DEFAULT_GRAPH_EXPANSION_LIMIT,
) -> List[Dict[str, Any]]:
    """
    Expand a list of top‑retrieved chunks using their graph relations, with batched fetching.

    Uses iterative BFS up to `expansion_depth` hops.
    """
    if not top_chunks:
        return []

    if expansion_depth <= 0:
        return top_chunks[:limit]

    if _batch_chunk_lookup is None:
        raise RuntimeError("Batch chunk lookup provider not configured.")

    start = time.perf_counter()

    # We'll collect all expanded entries here
    all_entries: List[Dict[str, Any]] = []

    # Track visited (file_id, chunk_id) to avoid duplicate requests
    visited: Set[Tuple[int, str]] = set()

    # Layer 0: seeds
    # Also add seeds as original entries
    current_layer = top_chunks[:]  # list of dicts
    for seed in current_layer:
        cid = seed.get("chunk_id")
        fid = seed.get("file_id")
        if cid and fid is not None:
            fid = int(fid)
            key = (fid, cid)
            if key not in visited:
                visited.add(key)
                entry = dict(seed)
                entry["graph_score"] = seed.get("retrieval_score", 1.0) * WEIGHT_ORIGINAL
                entry["graph_hop"] = 0
                entry["graph_relations"] = ["original"]
                entry["retrieval_score"] = seed.get("retrieval_score", 1.0)
                all_entries.append(entry)

    for hop in range(1, expansion_depth + 1):
        # Collect all relation IDs from the current layer
        layer_requests = []
        for chunk in current_layer:
            file_id = chunk.get("file_id")
            if file_id is None:
                continue
            file_id = int(file_id)
            chunk_id = chunk.get("chunk_id")
            if not chunk_id:
                continue
            seed_score = chunk.get("retrieval_score", 1.0)
            seed_file_id = chunk.get("graph_seed_file_id", file_id)
            seed_chunk_id = chunk.get("graph_seed_chunk_id", chunk_id)

            # Neighbors
            neighbor_ids = _collect_ids(chunk.get("neighbors", []), MAX_NEIGHBORS_PER_CHUNK)
            for fid, cid in neighbor_ids:
                if fid is None:
                    fid = file_id
                else:
                    fid = int(fid)
                key = (fid, cid)
                if key not in visited:
                    visited.add(key)
                    layer_requests.append({
                        "file_id": fid,
                        "chunk_id": cid,
                        "relation": "neighbor",
                        "weight": WEIGHT_NEIGHBOR,
                        "original_score": seed_score,
                        "seed_file_id": seed_file_id,
                        "seed_chunk_id": seed_chunk_id,
                    })

            # Parent
            parent_id = chunk.get("semantic_parent")
            if parent_id and isinstance(parent_id, str):
                fid = file_id
                key = (fid, parent_id)
                if key not in visited:
                    visited.add(key)
                    layer_requests.append({
                        "file_id": fid,
                        "chunk_id": parent_id,
                        "relation": "parent",
                        "weight": WEIGHT_PARENT,
                        "original_score": seed_score,
                        "seed_file_id": seed_file_id,
                        "seed_chunk_id": seed_chunk_id,
                    })

            # Children
            child_ids = _collect_ids(chunk.get("semantic_children", []), MAX_CHILDREN_PER_CHUNK)
            for fid, cid in child_ids:
                if fid is None:
                    fid = file_id
                else:
                    fid = int(fid)
                key = (fid, cid)
                if key not in visited:
                    visited.add(key)
                    layer_requests.append({
                        "file_id": fid,
                        "chunk_id": cid,
                        "relation": "child",
                        "weight": WEIGHT_CHILD,
                        "original_score": seed_score,
                        "seed_file_id": seed_file_id,
                        "seed_chunk_id": seed_chunk_id,
                    })

            # Cross-references
            cross_ids = _collect_ids(chunk.get("cross_refs", []), MAX_CROSS_REFS_PER_CHUNK)
            for fid, cid in cross_ids:
                if fid is None:
                    fid = file_id
                else:
                    fid = int(fid)
                key = (fid, cid)
                if key not in visited:
                    visited.add(key)
                    layer_requests.append({
                        "file_id": fid,
                        "chunk_id": cid,
                        "relation": "cross_ref",
                        "weight": WEIGHT_CROSSREF,
                        "original_score": seed_score,
                        "seed_file_id": seed_file_id,
                        "seed_chunk_id": seed_chunk_id,
                    })

        if not layer_requests:
            break

        # Batch fetch all chunks in this layer
        fetch_tuples = [(req["file_id"], req["chunk_id"]) for req in layer_requests]
        fetched = get_chunks_batch(pipeline_id, fetch_tuples)  # returns dict (file_id, chunk_id) -> chunk

        # Build next layer and add entries
        next_layer = []
        for req in layer_requests:
            chunk = fetched.get((req["file_id"], req["chunk_id"]))
            if not chunk:
                continue

            # Compute graph score with decay
            decay = DECAY_PER_HOP ** (hop - 1)
            graph_score = req["original_score"] * req["weight"] * decay

            # Create entry
            entry = dict(chunk)
            entry["graph_score"] = graph_score
            entry["graph_hop"] = hop
            entry["graph_relations"] = [req["relation"]]
            entry["retrieval_score"] = req["original_score"]
            entry["graph_seed_file_id"] = req["seed_file_id"]
            entry["graph_seed_chunk_id"] = req["seed_chunk_id"]
            all_entries.append(entry)

            # Add to next layer for further expansion
            if hop < expansion_depth:
                next_layer.append(entry)

        current_layer = next_layer
        if not current_layer:
            break

    # Deduplicate by (file_id, chunk_id), merging graph_relations
    dedup_map: Dict[Tuple[int, str], Dict[str, Any]] = {}
    for entry in all_entries:
        fid = entry.get("file_id")
        cid = entry.get("chunk_id")
        if fid is None or cid is None:
            continue
        fid = int(fid)
        key = (fid, cid)
        existing = dedup_map.get(key)
        if existing is None or entry.get("graph_score", 0.0) > existing.get("graph_score", 0.0):
            dedup_map[key] = entry
        else:
            # Merge relations
            if "graph_relations" in existing and "graph_relations" in entry:
                existing["graph_relations"] = list(set(existing["graph_relations"] + entry["graph_relations"]))

    # Sort by graph_score and truncate
    deduped = list(dedup_map.values())
    deduped.sort(key=lambda x: x.get("graph_score", 0.0), reverse=True)
    if len(deduped) > limit:
        deduped = deduped[:limit]

    # Clean up: remove old graph_relation field if present
    for d in deduped:
        if "graph_relation" in d:
            del d["graph_relation"]
        # Ensure graph_relations is always a list
        if "graph_relations" not in d or not isinstance(d["graph_relations"], list):
            d["graph_relations"] = []

    # Telemetry
    elapsed = time.perf_counter() - start
    relation_counts = defaultdict(int)
    for entry in deduped:
        for rel in entry.get("graph_relations", []):
            relation_counts[rel] += 1

    logger.info(
        f"Graph expansion: {len(top_chunks)} seeds, depth={expansion_depth}, "
        f"{len(all_entries)} candidates → {len(deduped)} final "
        f"({elapsed*1000:.1f} ms). Relations: {dict(relation_counts)}"
    )

    return deduped

# ---------------------------------------------------------------------------
# Backward‑compatible single‑chunk expansion (uses the main function)
# ---------------------------------------------------------------------------
def expand_single_chunk(
    chunk: Dict[str, Any],
    pipeline_id: int,
    depth: int = 1,
    limit_per_type: int = 10,
    visited: Optional[Set[Tuple[int, int, str]]] = None,
) -> List[Dict[str, Any]]:
    """
    Legacy function – kept for backward compatibility.
    """
    # Ignore visited (we'll use the batch version)
    return expand_graph_context([chunk], pipeline_id, expansion_depth=depth, limit=limit_per_type * 4)

# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------
__all__ = [
    "set_batch_chunk_lookup",
    "expand_graph_context",
    "expand_single_chunk",
]