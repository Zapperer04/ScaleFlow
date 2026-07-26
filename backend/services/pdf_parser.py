"""
pdf_parser.py — VLM-first document parser for ScaleFlow.

Architecture:
    Document → VLM API (PRIMARY) → Document Graph (from persisted artifact)
                           ↘ OCR Fallback (image-based) → Document Graph
    → Return ParseResult (document_graph + stats + page metadata)

Optimized: VLM path does NOT render images; rendering is deferred to OCR fallback.
Now uses the graph artifact persisted by document_preprocessor.py.
"""

from __future__ import annotations

import os
import sys
import json
import time
import logging
import threading
import gc
import uuid
import copy
import hashlib
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set

import numpy as np
import cv2
import psutil
import requests

# Internal config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# Optional imaging libraries
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

try:
    import pytesseract
    from pytesseract import Output
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

# Imports from document_preprocessor (updated API)
try:
    from services.document_preprocessor import (
        transcribe_pages,
        _transcribe_single_page_fallback,
        load_graph_artifact,
    )
    from services.gemini_rate_manager import RateLimitPauseRequired
    VLM_AVAILABLE = True
except ImportError as e:
    VLM_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning(f"VLM functions not available: {e}. Falling back to dummy implementations.")
    class RateLimitPauseRequired(Exception):
        pass
    def transcribe_pages(*args, **kwargs):
        raise NotImplementedError("document_preprocessor not available")
    def _transcribe_single_page_fallback(*args, **kwargs):
        raise NotImplementedError("document_preprocessor not available")
    def load_graph_artifact(*args, **kwargs):
        return None

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# Configuration limits
# ------------------------------------------------------------------------------
MAX_PAGES = config.PDF_MAX_PAGES
MEMORY_LIMIT_MB = config.PDF_MEMORY_LIMIT_MB
PARSE_TIMEOUT_S = config.PDF_PARSE_TIMEOUT_S
MEMORY_CHECK_EVERY = 25  # check RSS every N pages

# Custom exception for cooperative cancellation
class ParserCancelledError(Exception):
    """Raised when parsing is cancelled cooperatively."""
    pass


# ------------------------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------------------------
def _rss_mb() -> float:
    """Return current process resident memory in MB."""
    try:
        return psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
    except Exception:
        pass
    try:
        with open("/proc/self/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return float(line.split()[1]) / 1024
    except Exception:
        pass
    return 0.0


def _trace(trace_fn: Optional[Callable[[str], None]], message: str) -> None:
    logger.info(message)
    if trace_fn:
        try:
            trace_fn(message)
        except Exception:
            pass


def _check_cancellation(cancellation_check: Optional[Callable[[], bool]], msg: str = "Cancellation requested") -> None:
    """Raise ParserCancelledError if cancellation_check returns True."""
    if cancellation_check and cancellation_check():
        raise ParserCancelledError(msg)


def _close_pil_images(images: List[Any]) -> None:
    """Safely close PIL images to release resources."""
    if not images:
        return
    for img in images:
        if img is not None and hasattr(img, 'close'):
            try:
                img.close()
            except Exception:
                pass


def _generate_node_id(page_number: int, unique_suffix: str) -> str:
    """Generate a unique node ID for a page."""
    return f"p{page_number}_n_{unique_suffix}"


# ------------------------------------------------------------------------------
# Semantic category mapping
# ------------------------------------------------------------------------------
_SEMANTIC_MAP = {
    "heading": "heading",
    "heading_level_1": "heading",
    "heading_level_2": "heading",
    "heading_level_3": "heading",
    "heading_level_4": "heading",
    "title": "heading",
    "subtitle": "heading",
    "paragraph": "paragraph",
    "text": "paragraph",
    "body_text": "paragraph",
    "table": "table",
    "figure": "figure",
    "image": "figure",
    "list": "list",
    "list_item": "list",
    "bullet": "list",
    "caption": "caption",
    "footer": "footer",
    "header": "header",
    "equation": "equation",
    "formula": "equation",
}

def _normalize_semantic_category(raw_type: Optional[str]) -> str:
    """Map raw type to controlled semantic category."""
    if not raw_type:
        return "paragraph"
    raw_type_lower = raw_type.lower()
    return _SEMANTIC_MAP.get(raw_type_lower, "paragraph")


# ------------------------------------------------------------------------------
# BBox normalisation
# ------------------------------------------------------------------------------
def _normalize_bbox(bbox: Any) -> Dict[str, float]:
    """
    Normalise bounding box to a dict with x1, y1, x2, y2 keys.
    Supports both {'x1': ..., 'y1': ..., 'x2': ..., 'y2': ...} and [x1, y1, x2, y2].
    """
    if not bbox:
        return {"x1": 0.0, "y1": 0.0, "x2": 1.0, "y2": 1.0}
    if isinstance(bbox, dict):
        # Ensure all keys exist
        return {
            "x1": float(bbox.get("x1", 0.0)),
            "y1": float(bbox.get("y1", 0.0)),
            "x2": float(bbox.get("x2", 1.0)),
            "y2": float(bbox.get("y2", 1.0)),
        }
    if isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
        return {
            "x1": float(bbox[0]),
            "y1": float(bbox[1]),
            "x2": float(bbox[2]),
            "y2": float(bbox[3]),
        }
    return {"x1": 0.0, "y1": 0.0, "x2": 1.0, "y2": 1.0}


# ------------------------------------------------------------------------------
# Graph conversion from artifact to parser graph
# ------------------------------------------------------------------------------
def _convert_artifact_to_graph(artifact: Dict[str, Any], task_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Convert the artifact format (with blocks, tables) into the parser's internal
    document graph format (pages with nodes and edges).
    Preserves parent-child relationships via CONTAINS edges.
    Handles ID mapping, bbox normalisation, and forward compatibility.
    Now ensures chunker‑compatible fields: node_id, parent, children (resolved IDs).
    """
    if not artifact:
        return {}

    doc_info = artifact.get("document", {})
    pages_artifact = artifact.get("pages", [])
    metadata = artifact.get("metadata", {})

    pages_graph = []
    all_nodes = []
    node_id_to_reading_order = {}
    # Maps original block ID -> generated chunk_id
    id_mapping: Dict[str, str] = {}
    # Store nodes by original ID for parent/children resolution
    node_by_original_id: Dict[str, Dict] = {}

    # First pass: create nodes and store parent_original_id in each node
    for page_data in pages_artifact:
        page_num = page_data.get("page")
        if page_num is None:
            continue

        blocks = page_data.get("blocks", [])
        page_nodes = []

        # Process blocks
        for block in blocks:
            # Preserve original block ID if present
            original_id = block.get("id") or block.get("block_id")
            # Generate a deterministic chunk_id based on page and reading order,
            # but if original_id exists, use it as suffix for stability
            if original_id:
                chunk_id = _generate_node_id(page_num, f"block_{original_id}")
            else:
                chunk_id = _generate_node_id(page_num, f"block_{block.get('reading_order', 0)}")

            # Normalise bbox
            bbox = _normalize_bbox(block.get("bbox"))

            # Build node
            node = {
                "chunk_id": chunk_id,
                "text": block.get("text", ""),
                "structural_type": block.get("type", "paragraph"),
                "semantic_category": _normalize_semantic_category(block.get("type")),
                "confidence": block.get("confidence", 1.0),
                "reading_order": block.get("reading_order", 0),
                "bbox": bbox,
                "children": block.get("children", []),  # original IDs, will be mapped later
            }
            # Store original ID and parent original ID for later edge creation
            if original_id:
                node["original_id"] = original_id
            parent_orig = block.get("parent")
            if parent_orig:
                node["parent_original_id"] = parent_orig

            # Store mapping
            if original_id:
                id_mapping[original_id] = chunk_id
                node_by_original_id[original_id] = node
            else:
                # If no original ID, use chunk_id as its own mapping
                id_mapping[chunk_id] = chunk_id
                node_by_original_id[chunk_id] = node

            page_nodes.append(node)
            all_nodes.append(node)
            node_id_to_reading_order[chunk_id] = node.get("reading_order", 0)

        # Process tables (may have original IDs as well)
        tables = page_data.get("tables", [])
        for table in tables:
            original_id = table.get("id") or table.get("table_id")
            tbl_reading_order = table.get("reading_order", len(page_nodes) + 1)
            if original_id:
                chunk_id = _generate_node_id(page_num, f"table_{original_id}")
            else:
                chunk_id = _generate_node_id(page_num, f"table_{tbl_reading_order}")

            # Normalise bbox
            bbox = _normalize_bbox(table.get("bbox"))

            # Build node
            table_text = table.get("caption", "") + "\n" + "\n".join(
                [str(row) for row in table.get("rows", [])]
            )
            node = {
                "chunk_id": chunk_id,
                "text": table_text,
                "structural_type": "table",
                "semantic_category": "table",
                "confidence": table.get("confidence", 1.0),
                "reading_order": tbl_reading_order,
                "bbox": bbox,
                "children": [],  # tables might have children in future
                "table_data": {
                    "headers": table.get("headers", []),
                    "rows": table.get("rows", []),
                    "caption": table.get("caption", ""),
                }
            }
            if original_id:
                node["original_id"] = original_id
            parent_orig = table.get("parent")
            if parent_orig:
                node["parent_original_id"] = parent_orig

            # Store mapping
            if original_id:
                id_mapping[original_id] = chunk_id
                node_by_original_id[original_id] = node
            else:
                id_mapping[chunk_id] = chunk_id
                node_by_original_id[chunk_id] = node

            page_nodes.append(node)
            all_nodes.append(node)
            node_id_to_reading_order[chunk_id] = tbl_reading_order

        # Sort page nodes by reading_order
        page_nodes.sort(key=lambda n: n.get("reading_order", 0))

        pages_graph.append({
            "page_number": page_num,
            "nodes": page_nodes,
            "edges": []
        })

    # ---- Second pass: resolve parent and children to generated chunk IDs ----
    for node in all_nodes:
        # Ensure node_id and id are set (for chunker compatibility)
        node["node_id"] = node["chunk_id"]
        node["id"] = node["chunk_id"]

        # Resolve parent from parent_original_id
        parent_orig = node.get("parent_original_id")
        if parent_orig:
            parent_chunk = id_mapping.get(parent_orig)
            if parent_chunk:
                node["parent"] = parent_chunk
        # Resolve children list (original IDs -> chunk IDs)
        children_orig = node.get("children", [])
        resolved_children = []
        for child_orig in children_orig:
            child_chunk = id_mapping.get(child_orig)
            if child_chunk:
                resolved_children.append(child_chunk)
        if resolved_children:
            node["children"] = resolved_children
        # Keep original_id if needed
        # Keep parent_original_id if needed (optional)

    # ---- Build edges using the ID mapping and the stored parent_original_id ----
    edges = []
    edge_set = set()

    # Helper to add edge safely
    def add_edge(from_id, to_id, relation):
        if from_id and to_id and from_id != to_id:
            key = (from_id, to_id, relation)
            if key not in edge_set:
                edge_set.add(key)
                edges.append({
                    "from": from_id,
                    "to": to_id,
                    "relation": relation,
                })

    # Intra-page NEXT edges
    for pg in pages_graph:
        nodes = pg["nodes"]
        for i in range(len(nodes) - 1):
            add_edge(nodes[i]["chunk_id"], nodes[i+1]["chunk_id"], "NEXT")

    # Inter-page PAGE_NEXT edges
    for i in range(len(pages_graph) - 1):
        if pages_graph[i]["nodes"] and pages_graph[i+1]["nodes"]:
            add_edge(
                pages_graph[i]["nodes"][-1]["chunk_id"],
                pages_graph[i+1]["nodes"][0]["chunk_id"],
                "PAGE_NEXT"
            )

    # Build CONTAINS edges from parent_original_id stored in nodes (already resolved)
    for node in all_nodes:
        parent_chunk = node.get("parent")
        if parent_chunk:
            add_edge(parent_chunk, node["chunk_id"], "CONTAINS")
        # Also handle children list (already resolved)
        for child_chunk in node.get("children", []):
            if child_chunk:
                add_edge(node["chunk_id"], child_chunk, "CONTAINS")

    # Remove duplicate edges handled via set

    # Build final graph
    document_id = doc_info.get("filename", task_id or f"doc_{int(time.time())}")
    graph = {
        "document_id": document_id,
        "parser": metadata.get("parser", "gemini_vlm"),
        "schema_version": "1.0",
        "document_type": "MULTIMODAL",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "page_count": len(pages_graph),
        "pages": pages_graph,
        "edges": edges,
        "statistics": {
            "page_count": len(pages_graph),
            "node_count": len(all_nodes),
            "edge_count": len(edges),
            "vlm_success_pages": len(pages_graph),
            "ocr_fallback_pages": 0,
            "failed_pages": 0,
        },
        "document_metadata": {
            "source": "gemini_vlm",
            "parser": metadata.get("parser", "gemini_vlm"),
            "model_used": metadata.get("model_used", "unknown"),
        }
    }

    # Preserve any unknown metadata from the artifact (forward compatibility)
    for key, value in artifact.items():
        if key not in ("document", "pages", "metadata"):
            graph["document_metadata"][key] = value

    # Also copy any unknown fields from metadata into document_metadata if not already there
    for key, value in metadata.items():
        if key not in graph["document_metadata"]:
            graph["document_metadata"][key] = value

    return graph


# ------------------------------------------------------------------------------
# Helper to compute content hash (same as document_preprocessor)
# ------------------------------------------------------------------------------
def _get_content_hash(file_path: str) -> str:
    """Compute SHA256 hash of file content."""
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


# ------------------------------------------------------------------------------
# Graph validation and repair
# ------------------------------------------------------------------------------
def _validate_and_repair_graph(graph: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and repair document graph to ensure consistency.
    Returns a repaired copy of the graph; raises RuntimeError if repair is impossible.
    """
    # Work on a deep copy to avoid mutating the original
    graph_copy = copy.deepcopy(graph)

    # Ensure basic structure
    if not isinstance(graph_copy, dict):
        raise RuntimeError("Document graph is not a dict")
    if "pages" not in graph_copy or not isinstance(graph_copy["pages"], list):
        raise RuntimeError("Document graph missing 'pages' list")
    if "edges" not in graph_copy or not isinstance(graph_copy["edges"], list):
        graph_copy["edges"] = []

    # Validate pages and nodes
    all_node_ids: Set[str] = set()
    page_numbers = set()
    for pg in graph_copy["pages"]:
        if not isinstance(pg, dict):
            raise RuntimeError("Page entry is not a dict")
        pnum = pg.get("page_number")
        if not isinstance(pnum, int) or pnum < 1:
            raise RuntimeError(f"Invalid page_number: {pnum}")
        if pnum in page_numbers:
            raise RuntimeError(f"Duplicate page_number: {pnum}")
        page_numbers.add(pnum)

        # Validate nodes inside page
        nodes = pg.get("nodes")
        if not isinstance(nodes, list):
            raise RuntimeError(f"Page {pnum}: 'nodes' is not a list")
        for node in nodes:
            if not isinstance(node, dict):
                raise RuntimeError(f"Page {pnum}: node is not a dict")
            # Check required fields
            chunk_id = node.get("chunk_id")
            if not isinstance(chunk_id, str) or not chunk_id:
                # Regenerate chunk_id if missing
                new_id = _generate_node_id(pnum, uuid.uuid4().hex[:8])
                node["chunk_id"] = new_id
                chunk_id = new_id
                _trace(None, f"[VALIDATION] Regenerated missing chunk_id: {new_id}")

            # Check for duplicates
            if chunk_id in all_node_ids:
                # Regenerate with unique suffix
                new_id = _generate_node_id(pnum, uuid.uuid4().hex[:8])
                node["chunk_id"] = new_id
                _trace(None, f"[VALIDATION] Regenerated duplicate chunk_id: {new_id}")
                old_id = chunk_id
                chunk_id = new_id
                node["_old_chunk_id"] = old_id
            all_node_ids.add(chunk_id)

            # Ensure other required fields exist with defaults, but warn for bbox
            node.setdefault("text", "")
            node.setdefault("structural_type", "paragraph")
            node.setdefault("semantic_category", "body_text")
            node.setdefault("confidence", 1.0)
            node.setdefault("reading_order", 1)
            bbox = node.get("bbox")
            if bbox is None or not isinstance(bbox, dict):
                _trace(None, f"[VALIDATION] Warning: missing bbox for node {chunk_id}; setting default")
                node["bbox"] = {"x1": 0.0, "y1": 0.0, "x2": 1.0, "y2": 1.0}
            else:
                # Validate bbox coordinates
                for key in ["x1", "y1", "x2", "y2"]:
                    if key not in bbox or not isinstance(bbox[key], (int, float)):
                        _trace(None, f"[VALIDATION] Warning: invalid bbox for node {chunk_id}; correcting")
                        bbox[key] = 0.0

    # Update edges: replace old chunk_ids with new ones if needed
    edges = graph_copy["edges"]
    # Create mapping for regenerated ids
    id_map = {}
    for pg in graph_copy["pages"]:
        for node in pg.get("nodes", []):
            if "_old_chunk_id" in node:
                id_map[node["_old_chunk_id"]] = node["chunk_id"]
                del node["_old_chunk_id"]

    # Update edges
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        frm = edge.get("from")
        if frm in id_map:
            edge["from"] = id_map[frm]
        to = edge.get("to")
        if to in id_map:
            edge["to"] = id_map[to]

    # Validate edges: ensure all endpoints exist
    for edge in edges:
        frm = edge.get("from")
        to = edge.get("to")
        if frm and frm not in all_node_ids:
            raise RuntimeError(f"Edge references non-existent node: {frm}")
        if to and to not in all_node_ids:
            raise RuntimeError(f"Edge references non-existent node: {to}")

    # Remove duplicate edges
    edge_keys = set()
    unique_edges = []
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        key = (edge.get("from"), edge.get("to"), edge.get("relation"))
        if key not in edge_keys:
            edge_keys.add(key)
            unique_edges.append(edge)
    graph_copy["edges"] = unique_edges

    # Recompute statistics
    total_nodes = sum(len(pg.get("nodes", [])) for pg in graph_copy["pages"])
    total_edges = len(graph_copy["edges"])
    graph_copy["statistics"]["node_count"] = total_nodes
    graph_copy["statistics"]["edge_count"] = total_edges
    graph_copy["statistics"]["page_count"] = len(graph_copy["pages"])

    # Ensure page numbers are sequential from 1
    page_nums = sorted(pg["page_number"] for pg in graph_copy["pages"])
    if page_nums and page_nums != list(range(1, len(page_nums)+1)):
        # Reassign page numbers to be sequential
        for idx, pg in enumerate(sorted(graph_copy["pages"], key=lambda x: x["page_number"]), start=1):
            old_pnum = pg["page_number"]
            pg["page_number"] = idx
            # Update node chunk_ids to reflect new page number
            for node in pg.get("nodes", []):
                if node.get("chunk_id", "").startswith(f"p{old_pnum}_"):
                    node["chunk_id"] = node["chunk_id"].replace(f"p{old_pnum}_", f"p{idx}_", 1)
        _trace(None, f"[VALIDATION] Reassigned page numbers to sequential order")

    # Final validation
    page_nums_after = [pg["page_number"] for pg in graph_copy["pages"]]
    if sorted(page_nums_after) != list(range(1, len(page_nums_after)+1)):
        raise RuntimeError("Page numbers are still not sequential after repair")

    return graph_copy


# ------------------------------------------------------------------------------
# Page rendering (PDF → list of PIL images) — only used for OCR fallback
# ------------------------------------------------------------------------------
def _estimate_pdf_render_memory_mb(reader: Any, limit: int, target_dpi: int) -> float:
    bytes_per_pixel = 4.0
    estimated_mb = 0.0

    for page_index in range(limit):
        page = reader.pages[page_index]
        width_pt = float(getattr(page.mediabox, "width", 0) or 0)
        height_pt = float(getattr(page.mediabox, "height", 0) or 0)
        if width_pt <= 0 or height_pt <= 0:
            continue

        width_px = (width_pt / 72.0) * target_dpi
        height_px = (height_pt / 72.0) * target_dpi
        estimated_mb += (width_px * height_px * bytes_per_pixel) / (1024.0 * 1024.0)

    if estimated_mb <= 0:
        estimated_mb = limit * 25.0 * (target_dpi / 300.0) ** 2

    return estimated_mb


def render_pdf_pages(
    filepath: str,
    dpi: Optional[int] = None,
    max_pages: Optional[int] = None,
) -> List[Any]:
    """
    Convert PDF pages to PIL images.
    Raises RuntimeError if rendering fails or no pages produced.
    """
    if not PDF2IMAGE_AVAILABLE:
        raise RuntimeError("pdf2image is required to render PDF pages")

    # Determine page count using pypdf for validation only
    try:
        import pypdf
        reader = pypdf.PdfReader(filepath)
        total_pages = len(reader.pages)
    except Exception as e:
        raise RuntimeError(f"Cannot read PDF structure: {e}") from e

    limit = total_pages if max_pages is None else min(total_pages, max_pages)
    if limit <= 0:
        raise RuntimeError("PDF contains no pages to render")

    target_dpi = int(dpi or getattr(config, "PREPROCESS_TARGET_DPI", 300))
    poppler_path = getattr(config, "PREPROCESS_POPPLER_PATH", "") or os.getenv("PREPROCESS_POPPLER_PATH", "") or None

    # Self-healing adaptive DPI — use REAL available memory, no fake floor
    available_mb = psutil.virtual_memory().available / (1024.0 * 1024.0)
    # Safety: don't go below 256MB as a sanity floor, but do NOT inflate to 2048
    available_mb = max(available_mb, 256.0)

    for trial_dpi in [target_dpi, 150, 100, 75]:
        estimated_mb = _estimate_pdf_render_memory_mb(reader, limit, trial_dpi)
        if estimated_mb <= available_mb * 0.80:
            target_dpi = trial_dpi
            break
    else:
        target_dpi = 75

    # Re-check after DPI selection — hard reject if still too large
    estimated_mb = _estimate_pdf_render_memory_mb(reader, limit, target_dpi)
    if estimated_mb > available_mb * 0.85:
        raise MemoryError(
            f"Rendering {limit} pages at lowest {target_dpi} DPI requires ~{estimated_mb:.0f} MB, "
            f"exceeds safe memory budget (available: {available_mb:.0f} MB). "
            f"Consider splitting the document."
        )

    # Log chosen DPI for observability
    logger.info(f"[RENDER] Rendering {limit} pages at {target_dpi} DPI, estimated memory {estimated_mb:.1f} MB")

    # Batch render: never hold more than MAX_PAGES_PER_RENDER images in memory at once.
    MAX_PAGES_PER_RENDER = 50
    all_rendered: List[Any] = []
    for batch_start in range(1, limit + 1, MAX_PAGES_PER_RENDER):
        batch_end = min(batch_start + MAX_PAGES_PER_RENDER - 1, limit)
        batch_images = convert_from_path(
            filepath,
            first_page=batch_start,
            last_page=batch_end,
            dpi=target_dpi,
            poppler_path=poppler_path,
        )
        all_rendered.extend(img.convert("RGB") if img.mode != "RGB" else img for img in batch_images)
        # Explicitly free batch list to release memory before next batch
        del batch_images

    if not all_rendered:
        raise RuntimeError("PDF rendering produced no images")
    return all_rendered


def load_image_file(filepath: str) -> List[Any]:
    """Load a single image or multi-frame image as a list of PIL images."""
    if not PIL_AVAILABLE:
        raise RuntimeError("PIL is required to load images")
    with Image.open(filepath) as img:
        frame_count = getattr(img, "n_frames", 1) or 1
        images = []
        for i in range(frame_count):
            try:
                img.seek(i)
                images.append(img.copy().convert("RGB"))
            except EOFError:
                break
    if not images:
        raise RuntimeError("Image file produced no frames")
    return images


def render_document_pages(
    filepath: str,
    max_pages: Optional[int] = None,
    dpi: Optional[int] = None,
) -> List[Any]:
    """Render document pages (PDF or image) into a list of PIL images."""
    ext = os.path.splitext(filepath)[1].lower()
    try:
        if ext == ".pdf":
            return render_pdf_pages(filepath, dpi=dpi, max_pages=max_pages)
        elif ext in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}:
            images = load_image_file(filepath)
            if max_pages:
                images = images[:max_pages]
            return images
        else:
            raise ValueError(f"Unsupported file format: {ext}")
    except Exception as e:
        raise RuntimeError(f"Document rendering failed: {e}") from e


# ------------------------------------------------------------------------------
# Page analysis (table, signature, handwriting) — only for OCR fallback
# ------------------------------------------------------------------------------
def detect_table(pil_image: Image.Image) -> bool:
    """Return True if the page likely contains a table."""
    try:
        gray = np.array(pil_image.convert("L"))
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(
            edges, 1, np.pi / 180, threshold=50,
            minLineLength=gray.shape[1] // 8, maxLineGap=10,
        )
        if lines is None:
            return False
        h_lines = v_lines = 0
        for line in lines:
            x1, y1, x2, y2 = line[0]
            slope = abs(float(y2 - y1)) / (abs(float(x2 - x1)) + 1e-6)
            if slope < 0.2:
                h_lines += 1
            elif slope > 5.0:
                v_lines += 1
        return h_lines >= 3 and v_lines >= 2
    except Exception:
        return False


def detect_signature(pil_image: Image.Image) -> bool:
    """Return True if the bottom portion of the page likely contains a signature."""
    try:
        gray = np.array(pil_image.convert("L"))
        h, w = gray.shape
        roi = gray[int(h * 0.70):, :]
        binary = cv2.adaptiveThreshold(
            roi, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 11, 2,
        )
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 200:
                continue
            perimeter = cv2.arcLength(cnt, True)
            if perimeter == 0:
                continue
            circularity = 4 * 3.14159 * area / (perimeter ** 2)
            if 0.01 < circularity < 0.5 and area < (w * h * 0.30 * 0.25):
                return True
        return False
    except Exception:
        return False


def compute_handwriting_score(pil_image: Image.Image) -> float:
    """Estimate handwriting likelihood (0.0 - 1.0)."""
    try:
        gray = np.array(pil_image.convert("L"))
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 11, 2,
        )
        dist = cv2.distanceTransform(binary, cv2.DIST_L2, 5)
        ink_pixels = dist[binary > 0]
        sw_score = min(float(ink_pixels.std()) / 3.0, 1.0) if len(ink_pixels) > 0 else 0.0
        _, _, stats, _ = cv2.connectedComponentsWithStats(binary)
        areas = stats[1:, cv2.CC_STAT_AREA]
        cc_score = 0.0
        if len(areas) > 1:
            cv_ratio = float(areas.std()) / (float(areas.mean()) + 1e-6)
            cc_score = min(cv_ratio / 5.0, 1.0)
        block_means = []
        bh, bw = gray.shape
        bs = 32
        for y in range(0, bh - bs, bs):
            for x in range(0, bw - bs, bs):
                block_means.append(float(gray[y:y + bs, x:x + bs].mean()))
        density_score = 0.0
        if block_means:
            density_score = min(float(np.std(block_means)) / 255.0 * 4.0, 1.0)
        return sw_score * 0.5 + cc_score * 0.3 + density_score * 0.2
    except Exception:
        return 0.0


# ------------------------------------------------------------------------------
# Helper to build a document graph from page texts (fallback for VLM when artifact missing)
# ------------------------------------------------------------------------------
def _build_graph_from_texts(page_texts: Dict[int, str], task_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Build a minimal document graph from a dict of page_number -> text.
    Each page gets a single node with the full text.
    This is kept as a fallback when the rich artifact is not available.
    Also ensures chunker‑compatible fields (node_id, id, parent, children).
    """
    pages_graph = []
    for page_num, text in sorted(page_texts.items()):
        chunk_id = _generate_node_id(page_num, "vlm")
        node = {
            "chunk_id": chunk_id,
            "node_id": chunk_id,
            "id": chunk_id,
            "text": text,
            "structural_type": "paragraph",
            "semantic_category": "body_text",
            "confidence": 1.0,
            "reading_order": 1,
            "bbox": {"x1": 0.0, "y1": 0.0, "x2": 1.0, "y2": 1.0},
            "parent": None,
            "children": [],
        }
        pages_graph.append({
            "page_number": page_num,
            "nodes": [node],
            "edges": []
        })

    # Add inter-page edges
    edges = []
    for i in range(len(pages_graph) - 1):
        last_node = pages_graph[i]["nodes"][-1]
        first_node = pages_graph[i+1]["nodes"][0]
        edges.append({
            "from": last_node["chunk_id"],
            "to": first_node["chunk_id"],
            "relation": "PAGE_NEXT",
        })

    return {
        "document_id": task_id or f"doc_{int(time.time())}",
        "parser": "gemini_vlm",
        "schema_version": "1.0",
        "document_type": "MULTIMODAL",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "page_count": len(pages_graph),
        "pages": pages_graph,
        "edges": edges,
        "statistics": {
            "page_count": len(pages_graph),
            "node_count": len(pages_graph),  # one node per page
            "edge_count": len(edges),
            "vlm_success_pages": len(pages_graph),
            "ocr_fallback_pages": 0,
            "failed_pages": 0,
        },
    }


# ------------------------------------------------------------------------------
# Parse result dataclass
# ------------------------------------------------------------------------------
@dataclass
class ParseResult:
    document_graph: dict = field(default_factory=dict)
    stats: dict = field(default_factory=dict)
    pages: list = field(default_factory=list)


def execute_vlm_parse(
    filepath: str,
    vlm_provider_name: str,
    task_id: Optional[str] = None,
    progress_json: Optional[dict] = None,
    trace_fn: Optional[Callable[[str], None]] = None,
    on_page_completed: Optional[Callable[[int, Dict[str, Any]], None]] = None,
) -> Tuple[Optional[dict], List[dict], float, float]:
    """
    VLM-first document graph extraction (no rendering, load artifact).
    """
    vlm_start = time.time()
    
    # Extract page count
    try:
        import pypdf
        pdf_reader = pypdf.PdfReader(filepath)
        total_pages = len(pdf_reader.pages)
    except Exception as e:
        raise ValueError(f"FAILED_VALIDATION: Cannot read document: {e}") from e

    resume_page = 1
    completed_page_texts = {}
    
    if isinstance(progress_json, dict):
        resume_page = progress_json.get("resume_page", 1)
        raw_texts = progress_json.get("completed_page_texts", {})
        completed_page_texts = {int(k): v for k, v in raw_texts.items()}

    remaining_pages = list(range(resume_page, total_pages + 1))
    if remaining_pages:
        _trace(trace_fn, f"[PARSER] Resuming VLM parsing from page {resume_page} (remaining: {len(remaining_pages)} pages)")
        new_texts = transcribe_pages(
            file_path=filepath,
            page_numbers=remaining_pages,
            trace_fn=trace_fn,
            on_page_completed=on_page_completed
        )
        completed_page_texts.update(new_texts)
    else:
        _trace(trace_fn, "[PARSER] All pages already transcribed according to checkpoint progress.")

    page_texts = completed_page_texts
    vlm_extraction_duration = time.time() - vlm_start

    document_graph = None
    vlm_success = False
    vlm_mb = 0.0
    page_metadata = []

    if page_texts:
        content_hash = _get_content_hash(filepath)
        artifact = load_graph_artifact(content_hash)
        if artifact:
            _trace(trace_fn, "[PARSER] Loaded rich graph artifact")
            document_graph = _convert_artifact_to_graph(artifact, task_id)
            vlm_success = True
            vlm_mb = _rss_mb()
            _trace(trace_fn, f"[PARSER] VLM extraction succeeded (artifact) in {vlm_extraction_duration:.2f}s")
        else:
            _trace(trace_fn, "[PARSER] Artifact not found; falling back to simple graph from texts")
            document_graph = _build_graph_from_texts(page_texts, task_id)
            vlm_success = True
            vlm_mb = _rss_mb()
            _trace(trace_fn, f"[PARSER] VLM extraction succeeded (simple graph) in {vlm_extraction_duration:.2f}s")

        for pnum in range(1, total_pages + 1):
            page_metadata.append({
                "page_number": pnum,
                "extraction_method": "vlm",
                "parser_used": "gemini_vlm",
                "node_count": 0,
                "table_detected": False,
                "contains_signature": False,
                "contains_handwriting": False,
            })

        if on_page_completed and document_graph:
            for pg in document_graph.get("pages", []):
                pnum = pg.get("page_number")
                if pnum:
                    page_text = "\n".join([n.get("text", "") for n in pg.get("nodes", [])])
                    on_page_completed(pnum, {"text": page_text, "source": vlm_provider_name})
    else:
        _trace(trace_fn, "[PARSER] VLM returned empty page texts")

    return document_graph, page_metadata, vlm_extraction_duration, vlm_mb, total_pages


def execute_ocr_parse(
    filepath: str,
    task_id: Optional[str] = None,
    trace_fn: Optional[Callable[[str], None]] = None,
    on_page_completed: Optional[Callable[[int, Dict[str, Any]], None]] = None,
    cancellation_check: Optional[Callable[[], bool]] = None,
    timeout_check: Optional[Callable[[], bool]] = None,
) -> Tuple[Optional[dict], List[dict], float, float, float, float, int]:
    """
    OCR extraction path (rendering + transcription fallback).
    """
    ocr_start = time.time()
    
    # Extract page count
    try:
        import pypdf
        pdf_reader = pypdf.PdfReader(filepath)
        total_pages = len(pdf_reader.pages)
    except Exception as e:
        raise ValueError(f"FAILED_VALIDATION: Cannot read document: {e}") from e

    render_start = time.time()
    try:
        images = render_document_pages(filepath, max_pages=MAX_PAGES)
    except Exception as e:
        raise RuntimeError(f"Rendering for OCR failed: {e}") from e
    rendering_duration = time.time() - render_start
    render_mb = _rss_mb()
    _trace(trace_fn, f"[PARSER] Rendering for OCR completed in {rendering_duration:.2f}s, memory peak {render_mb:.1f}MB")

    MAX_DIM = 1800
    for idx, img in enumerate(images):
        if img is None:
            continue
        w, h = img.size
        if max(w, h) > MAX_DIM:
            scale = MAX_DIM / max(w, h)
            new_size = (int(w * scale), int(h * scale))
            images[idx] = img.resize(new_size, Image.LANCZOS if hasattr(Image, 'LANCZOS') else Image.BICUBIC)
            _trace(trace_fn, f"[PARSER] Resized page {idx+1} for OCR to {new_size}")

    page_metadata = []
    for idx, img in enumerate(images):
        if img is None:
            page_metadata.append({
                "page_number": idx+1,
                "extraction_method": "skipped",
                "parser_used": "none",
                "node_count": 0,
            })
            continue
        try:
            meta = {
                "page_number": idx + 1,
                "table_detected": detect_table(img),
                "contains_signature": detect_signature(img),
                "contains_handwriting": compute_handwriting_score(img) > 0.4,
                "extraction_method": "ocr",
                "parser_used": "tesseract",
                "node_count": 0,
            }
            page_metadata.append(meta)
        except Exception as e:
            _trace(trace_fn, f"[PARSER] Metadata extraction failed for page {idx+1}: {e}")
            page_metadata.append({
                "page_number": idx+1,
                "extraction_method": "metadata_error",
                "parser_used": "none",
                "node_count": 0,
            })

    pages_graph = []
    total_nodes = 0
    failed_pages = 0

    for idx, img in enumerate(images):
        _check_cancellation(cancellation_check, f"Cancelled before OCR page {idx+1}")
        if timeout_check and timeout_check():
            raise TimeoutError(f"Global timeout exceeded during OCR page {idx+1}")

        if img is None:
            continue
        page_number = idx + 1
        try:
            text = _transcribe_single_page_fallback(filepath, page_number, trace_fn)
            if text is not None:
                chunk_id = _generate_node_id(page_number, "ocr")
                node = {
                    "chunk_id": chunk_id,
                    "node_id": chunk_id,
                    "id": chunk_id,
                    "text": text,
                    "structural_type": "paragraph",
                    "semantic_category": "body_text",
                    "confidence": 0.8,
                    "reading_order": 1,
                    "bbox": {"x1": 0.0, "y1": 0.0, "x2": 1.0, "y2": 1.0},
                    "parent": None,
                    "children": [],
                }
                pages_graph.append({
                    "page_number": page_number,
                    "nodes": [node],
                    "edges": []
                })
                total_nodes += 1
                if idx < len(page_metadata):
                    page_metadata[idx]["node_count"] = 1
                if on_page_completed:
                    on_page_completed(page_number, {"text": text, "source": "ocr"})
            else:
                failed_pages += 1
                _trace(trace_fn, f"[PARSER] OCR fallback failed for page {page_number}")
        except Exception as e:
            logger.exception(f"OCR exception on page {page_number}")
            failed_pages += 1
            _trace(trace_fn, f"[PARSER] OCR exception on page {page_number}: {e}")
        finally:
            if hasattr(img, 'close'):
                try:
                    img.close()
                except Exception:
                    pass
            images[idx] = None
            if idx % MEMORY_CHECK_EVERY == 0 or _rss_mb() > MEMORY_LIMIT_MB * 0.8:
                gc.collect()

    ocr_fallback_duration = time.time() - ocr_start
    ocr_mb = _rss_mb()

    document_graph = {
        "document_id": task_id or f"doc_{int(time.time())}",
        "parser": "tesseract_ocr",
        "schema_version": "1.0",
        "document_type": "MULTIMODAL",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "page_count": total_pages,
        "pages": pages_graph,
        "edges": [],
        "statistics": {
            "page_count": total_pages,
            "node_count": total_nodes,
            "edge_count": 0,
            "vlm_success_pages": 0,
            "ocr_fallback_pages": len(pages_graph),
            "failed_pages": failed_pages,
        },
    }

    for i in range(len(pages_graph) - 1):
        last_node_prev = pages_graph[i]["nodes"][-1] if pages_graph[i].get("nodes") else None
        first_node_next = pages_graph[i+1]["nodes"][0] if pages_graph[i+1].get("nodes") else None
        if last_node_prev and first_node_next:
            document_graph.setdefault("edges", []).append({
                "from": last_node_prev["chunk_id"],
                "to": first_node_next["chunk_id"],
                "relation": "PAGE_NEXT",
            })
            document_graph["statistics"]["edge_count"] += 1

    try:
        _close_pil_images(images)
        del images
    except UnboundLocalError:
        pass
    gc.collect()

    return document_graph, page_metadata, ocr_fallback_duration, rendering_duration, render_mb, ocr_mb, total_pages


def parse_pdf(
    filepath: str,
    task_id: Optional[str] = None,
    lease_token: Optional[str] = None,
    progress_json: Optional[dict] = None,
    trace_fn: Optional[Callable[[str], None]] = None,
    api_url: Optional[str] = None,
    api_headers: Optional[dict] = None,
    skip_ocr: bool = False,
    document_type: str = "MULTIMODAL",
    routing_confidence: float = 1.0,
    parse_method_hint: str = "vlm_document_graph",
    enhanced_pages_path: Optional[str] = None,
    on_page_completed: Optional[Callable[[int, Dict[str, Any]], None]] = None,
    cancellation_check: Optional[Callable[[], bool]] = None,
    timeout_check: Optional[Callable[[], bool]] = None,
    vlm_provider_name: Optional[str] = None,
) -> ParseResult:
    """
    Orchestrator entry point that dispatches calls to Strategy Providers.
    """
    _check_cancellation(cancellation_check, "Cancelled before parsing started")
    if timeout_check and timeout_check():
        raise TimeoutError("Global timeout exceeded before parsing started")

    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Document not found: {filepath}")

    # Local imports inside function to completely avoid circular import issues
    from backend.infrastructure.providers.bootstrap import bootstrap_app

    container = bootstrap_app()
    provider_name = vlm_provider_name or "openrouter"
    
    # Delegate orchestration task directly to Strategy Provider
    provider = container.registry.get(provider_name)
    if not provider:
        provider = container.registry.get("openrouter")

    try:
        result = provider.parse_document(
            filepath=filepath,
            task_id=task_id,
            lease_token=lease_token,
            progress_json=progress_json,
            trace_fn=trace_fn,
            api_url=api_url,
            api_headers=api_headers,
            skip_ocr=skip_ocr,
            document_type=document_type,
            routing_confidence=routing_confidence,
            parse_method_hint=parse_method_hint,
            enhanced_pages_path=enhanced_pages_path,
            on_page_completed=on_page_completed,
        )
        return result
    except Exception as e:
        # Fallback to OCR provider directly on VLM failure
        if not skip_ocr and provider_name != "ocr":
            _trace(trace_fn, f"[ORCHESTRATOR] Provider {provider_name} failed. Falling back to OCR strategy...")
            ocr_provider = container.registry.get("ocr")
            return ocr_provider.parse_document(
                filepath=filepath,
                task_id=task_id,
                lease_token=lease_token,
                progress_json=progress_json,
                trace_fn=trace_fn,
                api_url=api_url,
                api_headers=api_headers,
                skip_ocr=skip_ocr,
                document_type=document_type,
                routing_confidence=routing_confidence,
                parse_method_hint=parse_method_hint,
                enhanced_pages_path=enhanced_pages_path,
                on_page_completed=on_page_completed,
            )
        raise e


# ------------------------------------------------------------------------------
# Compatibility alias
# ------------------------------------------------------------------------------
def extract_text_from_pdf(*args, **kwargs):
    """Old alias, now returns ParseResult."""
    return parse_pdf(*args, **kwargs)