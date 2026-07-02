"""
services/bm25_service.py — Whoosh‑backed BM25 sparse retrieval for ScaleFlow.
"""

import os
import shutil
import time
import logging
from typing import Any, Dict, List, Optional

from whoosh import index as whoosh_index
from whoosh.analysis import StandardAnalyzer
from whoosh.fields import Schema, ID, TEXT, NUMERIC, STORED
from whoosh.qparser import QueryParser
from whoosh import scoring

logger = logging.getLogger(__name__)

# Base directory for BM25 indexes
BASE_BM25_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "storage", "bm25"
)


def _get_index_dir(pipeline_id: int) -> str:
    """Return the absolute path to the BM25 index directory for a pipeline."""
    return os.path.join(BASE_BM25_DIR, f"pipeline_{pipeline_id}")


def _get_schema() -> Schema:
    """Define the Whoosh schema for graph‑native chunks with a unique composite key."""
    return Schema(
        # Unique composite key: pipeline_id + chunk_id to avoid collisions across pipelines
        chunk_uid=ID(stored=True, unique=True),
        pipeline_id=NUMERIC(stored=True),
        file_id=NUMERIC(stored=True),
        chunk_id=ID(stored=True),          # original chunk_id, not unique across pipelines
        chunk_index=NUMERIC(stored=True),
        section=STORED(),
        content_type=STORED(),
        bm25_text=TEXT(stored=True, analyzer=StandardAnalyzer()),
    )


def build_bm25_index(pipeline_id: int, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Create (or overwrite) a BM25 index for the given pipeline.

    Args:
        pipeline_id: ID of the pipeline.
        chunks: list of graph‑native chunk dictionaries.

    Returns:
        dict with 'success', 'documents_indexed', 'index_path'.
    """
    index_dir = _get_index_dir(pipeline_id)

    # Remove existing index to ensure a fresh build
    if os.path.exists(index_dir):
        logger.info(f"Removing existing BM25 index at {index_dir}")
        shutil.rmtree(index_dir)

    os.makedirs(index_dir, exist_ok=True)

    try:
        schema = _get_schema()
        ix = whoosh_index.create_in(index_dir, schema)
        # Use a memory buffer of 512 MB for faster indexing of large corpora
        writer = ix.writer(limitmb=512)

        indexed = 0
        for chunk in chunks:
            # Determine the text to index: bm25_text → embedding_text → text
            text = chunk.get("bm25_text") or chunk.get("embedding_text") or chunk.get("text") or ""
            if not text.strip():
                continue

            # Build unique composite ID
            chunk_id = str(chunk.get("chunk_id", ""))
            uid = f"{pipeline_id}_{chunk_id}" if chunk_id else None
            if not uid:
                # fallback: use chunk_index if chunk_id missing
                uid = f"{pipeline_id}_{chunk.get('chunk_index', 0)}"

            # Build document fields
            doc = {
                "chunk_uid": uid,
                "pipeline_id": int(pipeline_id),
                "file_id": int(chunk.get("file_id", 0)),
                "chunk_id": chunk_id,
                "chunk_index": int(chunk.get("chunk_index", 0)),
                "section": str(chunk.get("section", "")),
                "content_type": str(chunk.get("content_type", "paragraph")),
                "bm25_text": text,
            }
            writer.add_document(**doc)
            indexed += 1

        writer.commit()
        logger.info(f"BM25 index built: {indexed} documents at {index_dir}")
        return {
            "success": True,
            "documents_indexed": indexed,
            "index_path": index_dir,
        }

    except Exception as e:
        logger.exception(f"Failed to build BM25 index for pipeline {pipeline_id}: {e}")
        raise RuntimeError(f"BM25 index build failed: {e}") from e


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
        ix = whoosh_index.open_dir(index_dir)
        with ix.searcher(weighting=scoring.BM25F(B=0.75, K1=1.5)) as searcher:
            # Parse user query on the bm25_text field
            qp = QueryParser("bm25_text", schema=ix.schema)
            parsed_query = qp.parse(query)

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
    """
    Rebuild a BM25 index: delete existing index and create a new one.

    Args:
        pipeline_id: ID of the pipeline.
        chunks: list of graph‑native chunk dictionaries.

    Returns:
        dict with 'success', 'documents_indexed', 'index_path'.
    """
    delete_bm25_index(pipeline_id)
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
        ix = whoosh_index.open_dir(index_dir)
        doc_count = ix.doc_count()
        # Approximate storage size
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


# Module exports
__all__ = [
    "build_bm25_index",
    "retrieve_bm25",
    "delete_bm25_index",
    "rebuild_bm25_index",
    "get_bm25_stats",
]