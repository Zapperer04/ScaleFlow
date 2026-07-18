"""
services/bm25_service.py — Whoosh‑backed BM25 sparse retrieval for ScaleFlow.

Supports incremental updates, safe query parsing, and configurable analyzers.
"""

import os
import shutil
import time
import logging
import threading
from typing import Any, Dict, List, Optional

from whoosh import index as whoosh_index
from whoosh.analysis import StandardAnalyzer, StemmingAnalyzer
from whoosh.fields import Schema, ID, TEXT, NUMERIC, STORED
from whoosh.qparser import QueryParser
from whoosh import scoring
from whoosh.qparser import escape as whoosh_escape

logger = logging.getLogger(__name__)

# Base directory for BM25 indexes
BASE_BM25_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "storage", "bm25"
)

# Default writer memory limit (MB)
DEFAULT_WRITER_MEMORY = 512

# Analyzer selection: read from environment or config
try:
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import config
    USE_STEMMING = getattr(config, "BM25_USE_STEMMING", True)
except ImportError:
    USE_STEMMING = os.environ.get("BM25_USE_STEMMING", "true").lower() != "false"

ANALYZER = StemmingAnalyzer() if USE_STEMMING else StandardAnalyzer()

# ---------------------------------------------------------------------------
# Index cache (to avoid repeated open_dir)
# ---------------------------------------------------------------------------
_index_cache: Dict[int, whoosh_index.Index] = {}
_index_cache_lock = threading.Lock()

def _get_index(pipeline_id: int) -> Optional[whoosh_index.Index]:
    """Get a cached Index object, validating it still exists on disk."""
    index_dir = _get_index_dir(pipeline_id)
    # Check if index exists on disk
    if not os.path.exists(index_dir) or not whoosh_index.exists_in(index_dir):
        # Remove from cache if present
        with _index_cache_lock:
            _index_cache.pop(pipeline_id, None)
        return None

    with _index_cache_lock:
        # If we have a cached index, return it
        if pipeline_id in _index_cache:
            return _index_cache[pipeline_id]
        # Otherwise, open and cache
        try:
            idx = whoosh_index.open_dir(index_dir)
            _index_cache[pipeline_id] = idx
            return idx
        except Exception as e:
            logger.warning(f"Failed to open BM25 index for pipeline {pipeline_id}: {e}")
            _index_cache.pop(pipeline_id, None)
            return None

def _invalidate_index_cache(pipeline_id: int) -> None:
    with _index_cache_lock:
        _index_cache.pop(pipeline_id, None)

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def _get_index_dir(pipeline_id: int) -> str:
    return os.path.join(BASE_BM25_DIR, f"pipeline_{pipeline_id}")

def _get_schema() -> Schema:
    return Schema(
        chunk_uid=ID(stored=True, unique=True),
        pipeline_id=NUMERIC(stored=True),
        file_id=NUMERIC(stored=True),
        chunk_id=ID(stored=True),
        chunk_index=NUMERIC(stored=True),
        section=STORED(),
        content_type=STORED(),
        bm25_text=TEXT(stored=True, analyzer=ANALYZER),
    )

def _build_doc_from_chunk(pipeline_id: int, chunk: Dict[str, Any]) -> Dict[str, Any]:
    text = chunk.get("bm25_text") or chunk.get("embedding_text") or chunk.get("text") or ""
    chunk_id = str(chunk.get("chunk_id", ""))
    uid = f"{pipeline_id}_{chunk_id}" if chunk_id else f"{pipeline_id}_{chunk.get('chunk_index', 0)}"
    return {
        "chunk_uid": uid,
        "pipeline_id": int(pipeline_id),
        "file_id": int(chunk.get("file_id", 0)),
        "chunk_id": chunk_id,
        "chunk_index": int(chunk.get("chunk_index", 0)),
        "section": str(chunk.get("section", "")),
        "content_type": str(chunk.get("content_type", "paragraph")),
        "bm25_text": text,
    }

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def build_bm25_index(
    pipeline_id: int,
    chunks: List[Dict[str, Any]],
    writer_memory: int = DEFAULT_WRITER_MEMORY
) -> Dict[str, Any]:
    """
    Create (or overwrite) a BM25 index for the given pipeline.

    Args:
        pipeline_id: ID of the pipeline.
        chunks: list of graph‑native chunk dictionaries.
        writer_memory: memory limit in MB for the index writer.

    Returns:
        dict with 'success', 'documents_indexed', 'index_path'.
    """
    index_dir = _get_index_dir(pipeline_id)
    if os.path.exists(index_dir):
        logger.info(f"Removing existing BM25 index at {index_dir}")
        shutil.rmtree(index_dir)

    os.makedirs(index_dir, exist_ok=True)

    try:
        schema = _get_schema()
        ix = whoosh_index.create_in(index_dir, schema)
        writer = ix.writer(limitmb=writer_memory)

        indexed = 0
        for chunk in chunks:
            text = chunk.get("bm25_text") or chunk.get("embedding_text") or chunk.get("text") or ""
            if not text.strip():
                continue
            doc = _build_doc_from_chunk(pipeline_id, chunk)
            writer.add_document(**doc)
            indexed += 1

        writer.commit()
        _invalidate_index_cache(pipeline_id)
        logger.info(f"BM25 index built: {indexed} documents at {index_dir}")
        return {
            "success": True,
            "documents_indexed": indexed,
            "index_path": index_dir,
        }
    except Exception as e:
        logger.exception(f"Failed to build BM25 index for pipeline {pipeline_id}: {e}")
        raise RuntimeError(f"BM25 index build failed: {e}") from e

def update_bm25_index(
    pipeline_id: int,
    chunks: List[Dict[str, Any]],
    mode: str = "upsert",
    writer_memory: int = DEFAULT_WRITER_MEMORY
) -> Dict[str, Any]:
    """
    Incrementally update the BM25 index for a pipeline.

    Modes:
        - 'upsert': add or update each chunk.
        - 'delete': remove each chunk by chunk_id.
        - 'replace': same as build_bm25_index (full rebuild).

    Returns:
        dict with 'success', 'documents_processed', 'index_path'.
    """
    if mode == "replace":
        return build_bm25_index(pipeline_id, chunks, writer_memory)

    index_dir = _get_index_dir(pipeline_id)
    if not os.path.exists(index_dir) or not whoosh_index.exists_in(index_dir):
        logger.info(f"BM25 index for pipeline {pipeline_id} not found; building new index.")
        return build_bm25_index(pipeline_id, chunks, writer_memory)

    ix = _get_index(pipeline_id)
    if ix is None:
        return build_bm25_index(pipeline_id, chunks, writer_memory)

    try:
        writer = ix.writer(limitmb=writer_memory)
        processed = 0

        if mode == "delete":
            for chunk in chunks:
                chunk_id = str(chunk.get("chunk_id", ""))
                if not chunk_id:
                    continue
                uid = f"{pipeline_id}_{chunk_id}"
                writer.delete_by_term("chunk_uid", uid)
                processed += 1
        else:  # upsert
            for chunk in chunks:
                text = chunk.get("bm25_text") or chunk.get("embedding_text") or chunk.get("text") or ""
                if not text.strip():
                    # If text is empty, delete the document (or skip)
                    continue
                doc = _build_doc_from_chunk(pipeline_id, chunk)
                # Upsert: update_document uses unique key to replace
                # Pass the whole doc dict; it contains 'chunk_uid' as key
                writer.update_document(**doc)
                processed += 1

        writer.commit()
        _invalidate_index_cache(pipeline_id)
        logger.info(f"BM25 index updated (mode={mode}): {processed} documents processed at {index_dir}")
        return {
            "success": True,
            "documents_processed": processed,
            "index_path": index_dir,
        }
    except Exception as e:
        logger.exception(f"Failed to update BM25 index for pipeline {pipeline_id}: {e}")
        raise RuntimeError(f"BM25 index update failed: {e}") from e

def retrieve_bm25(
    pipeline_id: int, query: str, top_k: int = 30
) -> List[Dict[str, Any]]:
    """
    Search the BM25 index for a pipeline.

    Args:
        pipeline_id: ID of the pipeline.
        query: search string.
        top_k: maximum number of results.

    Returns:
        list of dicts with keys: score, chunk_id, pipeline_id, file_id, chunk_index,
        section, content_type, chunk_text, plus retrieval metadata.
    """
    if not query.strip():
        return []

    index_dir = _get_index_dir(pipeline_id)
    if not os.path.exists(index_dir) or not whoosh_index.exists_in(index_dir):
        logger.warning(f"BM25 index for pipeline {pipeline_id} does not exist")
        return []

    start = time.perf_counter()
    try:
        ix = _get_index(pipeline_id)
        if ix is None:
            logger.warning(f"Failed to open BM25 index for pipeline {pipeline_id}")
            return []

        with ix.searcher(weighting=scoring.BM25F(B=0.75, K1=1.5)) as searcher:
            # Safely parse the query
            try:
                qp = QueryParser("bm25_text", schema=ix.schema)
                parsed_query = qp.parse(query)
            except Exception:
                # Fallback: escape the query and treat as a phrase
                escaped = whoosh_escape(query)
                qp = QueryParser("bm25_text", schema=ix.schema)
                parsed_query = qp.parse(f'"{escaped}"')
                logger.debug(f"Query parsing fallback: using escaped phrase '{escaped}'")

            results = searcher.search(parsed_query, limit=top_k, terms=True)
            hits = []
            for hit in results:
                hits.append(
                    {
                        "score": round(hit.score, 6),
                        "retrieval_type": "bm25",
                        "retrieval_score": round(hit.score, 6),
                        "retrieval_backend": "whoosh",
                        "chunk_id": hit.get("chunk_id"),
                        "pipeline_id": hit.get("pipeline_id"),
                        "file_id": hit.get("file_id"),
                        "chunk_index": hit.get("chunk_index"),
                        "section": hit.get("section"),
                        "content_type": hit.get("content_type"),
                        "chunk_text": hit.get("bm25_text") or "",
                    }
                )

        elapsed = time.perf_counter() - start
        logger.info(
            f"BM25 retrieval for pipeline {pipeline_id}: query='{query}' returned "
            f"{len(hits)} results in {elapsed:.4f}s"
        )
        return hits

    except Exception as e:
        logger.exception(f"BM25 retrieval error for pipeline {pipeline_id}: {e}")
        raise RuntimeError(f"BM25 retrieval failed: {e}") from e

def delete_bm25_index(pipeline_id: int) -> bool:
    """
    Remove the BM25 index directory for a pipeline.

    Returns True if successful, False otherwise.
    """
    _invalidate_index_cache(pipeline_id)
    index_dir = _get_index_dir(pipeline_id)
    if not os.path.exists(index_dir):
        logger.info(f"BM25 index for pipeline {pipeline_id} not found; nothing to delete")
        return True
    try:
        shutil.rmtree(index_dir)
        logger.info(f"BM25 index for pipeline {pipeline_id} deleted")
        return True
    except Exception as e:
        logger.exception(f"Failed to delete BM25 index for pipeline {pipeline_id}: {e}")
        return False

def rebuild_bm25_index(pipeline_id: int, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Alias for build_bm25_index."""
    return build_bm25_index(pipeline_id, chunks)

def get_bm25_stats(pipeline_id: int) -> Dict[str, Any]:
    """
    Return statistics about the BM25 index for a pipeline.

    Returns:
        dict with 'exists', 'document_count', 'storage_size_mb', 'index_path'.
    """
    index_dir = _get_index_dir(pipeline_id)
    exists = os.path.exists(index_dir) and whoosh_index.exists_in(index_dir)
    if not exists:
        return {
            "exists": False,
            "document_count": 0,
            "storage_size_mb": 0.0,
            "index_path": index_dir,
        }

    try:
        ix = _get_index(pipeline_id)
        if ix is None:
            raise RuntimeError("Could not open index")
        doc_count = ix.doc_count()
        total_size = 0
        for dirpath, _, filenames in os.walk(index_dir):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if os.path.isfile(fp):
                    total_size += os.path.getsize(fp)
        size_mb = round(total_size / (1024 * 1024), 3)
        return {
            "exists": True,
            "document_count": doc_count,
            "storage_size_mb": size_mb,
            "index_path": index_dir,
        }
    except Exception as e:
        logger.exception(f"Error reading BM25 stats for pipeline {pipeline_id}: {e}")
        return {
            "exists": True,
            "document_count": 0,
            "storage_size_mb": 0.0,
            "index_path": index_dir,
        }

# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------
__all__ = [
    "build_bm25_index",
    "update_bm25_index",
    "retrieve_bm25",
    "delete_bm25_index",
    "rebuild_bm25_index",
    "get_bm25_stats",
]