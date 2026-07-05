"""
pdf_parser.py — VLM-first document parser for ScaleFlow.

Architecture:
    Document → Render Pages → VLM Parsing (PRIMARY) → Document Graph
                           ↘ OCR Fallback → Document Graph
    → Return ParseResult (document_graph + stats + page metadata)
"""

from __future__ import annotations

import os
import sys
import json
import time
import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

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

# VLM document graph extraction (already implemented)
# NOTE: _ocr_fallback_page is defined inside services.document_preprocessor
try:
    from services.document_preprocessor import (
        execute_vlm_document_graph_extraction,
        _ocr_fallback_page,
    )
    VLM_AVAILABLE = True
except ImportError:
    VLM_AVAILABLE = False

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# Configuration limits
# ------------------------------------------------------------------------------
MAX_PAGES = config.PDF_MAX_PAGES
MEMORY_LIMIT_MB = config.PDF_MEMORY_LIMIT_MB
PARSE_TIMEOUT_S = config.PDF_PARSE_TIMEOUT_S
MEMORY_CHECK_EVERY = 50  # check RSS every N pages


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


# ------------------------------------------------------------------------------
# Page rendering (PDF → list of PIL images)
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

    # Memory estimate based on actual page dimensions at the target DPI.
    estimated_mb = _estimate_pdf_render_memory_mb(reader, limit, target_dpi)
    available_mb = psutil.virtual_memory().available / (1024.0 * 1024.0)
    if estimated_mb > available_mb * 0.70:
        raise MemoryError(
            f"Rendering {limit} pages at {target_dpi} DPI requires ~{estimated_mb:.0f} MB, exceeds safe memory budget"
        )

    images = convert_from_path(
        filepath,
        first_page=1,
        last_page=limit,
        dpi=target_dpi,
        poppler_path=poppler_path,
    )
    # Ensure RGB mode
    rendered = [img.convert("RGB") if img.mode != "RGB" else img for img in images]
    if not rendered:
        raise RuntimeError("PDF rendering produced no images")
    return rendered


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
    if ext == ".pdf":
        return render_pdf_pages(filepath, dpi=dpi, max_pages=max_pages)
    elif ext in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}:
        images = load_image_file(filepath)
        if max_pages:
            images = images[:max_pages]
        return images
    else:
        raise ValueError(f"Unsupported file format: {ext}")


# ------------------------------------------------------------------------------
# Page analysis (table, signature, handwriting)
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
# Parse result dataclass
# ------------------------------------------------------------------------------
@dataclass
class ParseResult:
    document_graph: dict = field(default_factory=dict)
    stats: dict = field(default_factory=dict)
    pages: list = field(default_factory=list)


# ------------------------------------------------------------------------------
# Main VLM-first parse pipeline
# ------------------------------------------------------------------------------
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
    enhanced_pages_path: Optional[str] = None
) -> ParseResult:
    """
    Parse a document into a structured document graph using VLM as primary method.

    Args:
        filepath: Path to document (PDF or image).
        task_id: ScaleFlow task identifier.
        lease_token: Worker lease token for progress updates.
        progress_json: Previous progress state (checkpoint).
        trace_fn: Callback for trace events.
        api_url: ScaleFlow API URL for progress PATCH.
        api_headers: Headers for API requests.
        skip_ocr: If True, do not fallback to OCR on VLM failure.
        document_type: (compatibility) Expected document type.
        routing_confidence: (compatibility) Routing confidence.
        parse_method_hint: (compatibility) Hint for parsing method.
        enhanced_pages_path: Path to pre-enhanced pages directory.

    Returns:
        ParseResult with document_graph, stats, and page metadata.
    """
    # --------------------------------------------------------------------------
    # 1. Validation & governance
    # --------------------------------------------------------------------------
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Document not found: {filepath}")

    file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
    _trace(trace_fn, f"[PARSER] File: {os.path.basename(filepath)} ({file_size_mb:.1f} MB)")
    _trace(trace_fn, "[PARSER] VLM-first extraction pipeline")

    # Get page count from PDF metadata (pypdf) without full extraction
    try:
        import pypdf
        pdf_reader = pypdf.PdfReader(filepath)
        total_pages = len(pdf_reader.pages)
    except Exception as e:
        raise ValueError(f"FAILED_VALIDATION: Cannot read document: {e}") from e

    _trace(trace_fn, f"[PARSER] Total pages: {total_pages}")

    # Circuit breaker: suspect huge page count vs file size
    if total_pages > (file_size_mb * 3000) + 100:
        raise ValueError(
            f"FAILED_VALIDATION: Anomalous {total_pages} pages for {file_size_mb:.1f} MB file."
        )

    if total_pages > MAX_PAGES:
        raise RuntimeError(
            f"Governance Limit Exceeded: {total_pages} pages (max {MAX_PAGES})."
        )

    # Memory guard before rendering all pages
    if total_pages > 0:
        _trace(trace_fn, f"[PARSER] Rendering {total_pages} pages for VLM processing...")

    # --------------------------------------------------------------------------
    # 2. Render pages
    # --------------------------------------------------------------------------
    start_time = time.time()
    try:
        images = render_document_pages(filepath, max_pages=MAX_PAGES)
    except Exception as e:
        raise RuntimeError(f"Rendering failed: {e}") from e

    if not images:
        raise RuntimeError("No pages rendered from document")

    # Apply optional image size limit for VLM (avoid huge payloads)
    MAX_DIM = 1800
    for idx, img in enumerate(images):
        w, h = img.size
        if max(w, h) > MAX_DIM:
            scale = MAX_DIM / max(w, h)
            new_size = (int(w * scale), int(h * scale))
            images[idx] = img.resize(new_size, Image.LANCZOS if hasattr(Image, 'LANCZOS') else Image.BICUBIC)
            _trace(trace_fn, f"[PARSER] Resized page {idx+1} to {new_size}")

    # --------------------------------------------------------------------------
    # 3. Page‑level metadata extraction (table, signature, handwriting)
    # --------------------------------------------------------------------------
    page_metadata = []
    for idx, img in enumerate(images):
        meta = {
            "page_number": idx + 1,
            "table_detected": detect_table(img),
            "contains_signature": detect_signature(img),
            "contains_handwriting": compute_handwriting_score(img) > 0.4,
            "extraction_method": "vlm",  # default, may change after fallback
            "parser_used": "gemini_vlm",
            "node_count": 0,
        }
        page_metadata.append(meta)

    # --------------------------------------------------------------------------
    # 4. Primary: VLM document graph extraction
    # --------------------------------------------------------------------------
    document_graph = None
    vlm_success = False
    ocr_fallback_used = False

    if VLM_AVAILABLE:
        _trace(trace_fn, "[PARSER] Starting VLM document graph extraction...")
        try:
            # Note: execute_vlm_document_graph_extraction already handles its own threading,
            # and returns a full document graph.
            document_graph = execute_vlm_document_graph_extraction(
                images=images,
                pipeline_id=task_id,
                max_workers=2,
                trace_fn=trace_fn,
            )
            vlm_success = True
            _trace(trace_fn, "[PARSER] VLM extraction succeeded")
        except Exception as e:
            _trace(trace_fn, f"[PARSER] VLM extraction failed: {e}")
            document_graph = None
    else:
        _trace(trace_fn, "[PARSER] VLM module not available, proceeding to OCR fallback")

    # --------------------------------------------------------------------------
    # 5. OCR fallback (if VLM failed or unavailable)
    # --------------------------------------------------------------------------
    if (not vlm_success or document_graph is None) and not skip_ocr:
        _trace(trace_fn, "[PARSER] Falling back to OCR-based document graph")
        ocr_fallback_used = True
        pages_graph = []
        failed_pages = 0
        total_nodes = 0
        total_edges = 0

        for idx, img in enumerate(images):
            page_number = idx + 1
            try:
                pg = _ocr_fallback_page(img, page_number)
                if pg:
                    pages_graph.append(pg)
                    nodes = pg.get("nodes", [])
                    edges = pg.get("edges", [])
                    total_nodes += len(nodes)
                    total_edges += len(edges)
                    page_metadata[idx]["extraction_method"] = "ocr"
                    page_metadata[idx]["parser_used"] = "tesseract"
                    page_metadata[idx]["node_count"] = len(nodes)
                else:
                    failed_pages += 1
                    _trace(trace_fn, f"[PARSER] OCR fallback failed for page {page_number}")
            except Exception as e:
                _trace(trace_fn, f"[PARSER] OCR exception on page {page_number}: {e}")
                failed_pages += 1

        # Build a document graph structure similar to VLM output
        document_graph = {
            "document_id": task_id or f"doc_{int(time.time())}",
            "parser": "tesseract_ocr",
            "schema_version": "1.0",
            "document_type": "MULTIMODAL",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "page_count": len(images),
            "pages": pages_graph,
            "edges": [],  # OCR fallback per-page edges already inside pages
            "statistics": {
                "page_count": len(images),
                "node_count": total_nodes,
                "edge_count": total_edges,
                "vlm_success_pages": 0,
                "ocr_fallback_pages": len(pages_graph),
                "failed_pages": failed_pages,
            },
        }

        # Add inter‑page PAGE_NEXT edges for consistency
        for i in range(len(pages_graph) - 1):
            last_node_prev = pages_graph[i]["nodes"][-1] if pages_graph[i].get("nodes") else None
            first_node_next = pages_graph[i+1]["nodes"][0] if pages_graph[i+1].get("nodes") else None
            if last_node_prev and first_node_next:
                document_graph.setdefault("edges", []).append({
                    "from": last_node_prev["chunk_id"],
                    "to": first_node_next["chunk_id"],
                    "relation": "PAGE_NEXT",
                })

    elif not vlm_success and skip_ocr:
        # OCR not allowed, return empty graph with failure note
        document_graph = {
            "document_id": task_id or "unknown",
            "parser": "none",
            "schema_version": "1.0",
            "document_type": "MULTIMODAL",
            "pages": [],
            "edges": [],
            "statistics": {"failed_pages": len(images)},
        }

    # --------------------------------------------------------------------------
    # 6. Populate page metadata with VLM node counts if available
    # --------------------------------------------------------------------------
    if vlm_success and document_graph:
        for pg in document_graph.get("pages", []):
            pnum = pg.get("page_number")
            if pnum and 1 <= pnum <= len(page_metadata):
                page_metadata[pnum-1]["node_count"] = len(pg.get("nodes", []))
                page_metadata[pnum-1]["parser_used"] = "gemini_vlm"

    # --------------------------------------------------------------------------
    # 7. Compute final statistics
    # --------------------------------------------------------------------------
    duration = round(time.time() - start_time, 2)
    vlm_pages = document_graph.get("statistics", {}).get("vlm_success_pages", 0) if (document_graph and vlm_success) else 0
    ocr_pages = document_graph.get("statistics", {}).get("ocr_fallback_pages", 0) if (document_graph and (ocr_fallback_used or vlm_success)) else 0
    failed_pages = document_graph.get("statistics", {}).get("failed_pages", 0)
    node_count = document_graph.get("statistics", {}).get("node_count", sum(m["node_count"] for m in page_metadata))
    edge_count = document_graph.get("statistics", {}).get("edge_count", 0)

    parser_name = "gemini_vlm"
    if vlm_success:
        if ocr_pages > 0:
            parser_name = "ocr_fallback" if vlm_pages == 0 else "gemini_vlm_ocr_fallback"
    elif ocr_fallback_used:
        parser_name = "tesseract_ocr"
    else:
        parser_name = "none"

    stats = {
        "parser": parser_name,
        "total_pages": total_pages,
        "processed_pages": len(images),
        "vlm_pages": vlm_pages,
        "ocr_pages": ocr_pages,
        "failed_pages": failed_pages,
        "node_count": node_count,
        "edge_count": edge_count,
        "duration_seconds": duration,
        "memory_peak_mb": _rss_mb(),
        "page_failures": [],
        "timings": {
            "rendering_duration": 0.0,  # could be measured but simple
            "vlm_extraction_duration": 0.0,
            "ocr_fallback_duration": 0.0,
        },
    }

    _trace(trace_fn, f"[PARSER] Extraction complete: {stats}")

    # --------------------------------------------------------------------------
    # 8. Return structured result
    # --------------------------------------------------------------------------
    return ParseResult(
        document_graph=document_graph,
        stats=stats,
        pages=page_metadata,
    )


# ------------------------------------------------------------------------------
# Compatibility alias
# ------------------------------------------------------------------------------
def extract_text_from_pdf(*args, **kwargs):
    """Old alias, now returns ParseResult."""
    return parse_pdf(*args, **kwargs)