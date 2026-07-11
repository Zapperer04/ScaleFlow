import os
import sys
import io
import json
import time
import math
import base64
import logging
import threading
import concurrent.futures
import re
import gc
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Set

import numpy as np
import cv2
import psutil
import pypdf
import requests

_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(_CURRENT_DIR)
if _BACKEND_DIR not in sys.path:
    sys.path.append(_BACKEND_DIR)

import config

try:
    from PIL import Image, ImageOps
    PIL_AVAILABLE = True
except Exception:
    Image = None
    ImageOps = None
    PIL_AVAILABLE = False

try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except Exception:
    convert_from_path = None
    PDF2IMAGE_AVAILABLE = False

try:
    import pytesseract
    from pytesseract import Output
    PYTESSERACT_AVAILABLE = True
except Exception:
    pytesseract = None
    Output = None
    PYTESSERACT_AVAILABLE = False

CV2_AVAILABLE = True

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# Configuration (from environment or config.py)
# ------------------------------------------------------------------------------
PAGE_PARSE_TIMEOUT_SECONDS = int(os.getenv("PAGE_PARSE_TIMEOUT_SECONDS", getattr(config, "PAGE_PARSE_TIMEOUT_SECONDS", 120)))
MAX_DOCUMENT_PARSE_SECONDS = int(os.getenv("MAX_DOCUMENT_PARSE_SECONDS", getattr(config, "MAX_DOCUMENT_PARSE_SECONDS", 3600)))
HEARTBEAT_INTERVAL_SECONDS = int(os.getenv("HEARTBEAT_INTERVAL_SECONDS", getattr(config, "HEARTBEAT_INTERVAL_SECONDS", 10)))
MAX_PAGE_RETRIES = int(os.getenv("MAX_PAGE_RETRIES", getattr(config, "MAX_PAGE_RETRIES", 3)))
MAX_RETRY_DURATION_SECONDS = int(os.getenv("MAX_RETRY_DURATION_SECONDS", getattr(config, "MAX_RETRY_DURATION_SECONDS", 180)))
HTTP_CONNECT_TIMEOUT = int(os.getenv("HTTP_CONNECT_TIMEOUT", getattr(config, "HTTP_CONNECT_TIMEOUT", 15)))
HTTP_READ_TIMEOUT = int(os.getenv("HTTP_READ_TIMEOUT", getattr(config, "HTTP_READ_TIMEOUT", 120)))
MEMORY_GC_INTERVAL = int(os.getenv("MEMORY_GC_INTERVAL", getattr(config, "MEMORY_GC_INTERVAL", 10)))
MAX_GRAPH_EDGES = int(os.getenv("MAX_GRAPH_EDGES", getattr(config, "MAX_GRAPH_EDGES", 5000)))
MAX_ACTIVE_PAGES = int(os.getenv("MAX_ACTIVE_PAGES", getattr(config, "MAX_ACTIVE_PAGES", 2)))
FAILURE_RATIO_THRESHOLD = float(os.getenv("FAILURE_RATIO_THRESHOLD", getattr(config, "FAILURE_RATIO_THRESHOLD", 0.5)))
RECOVERABLE_JSON_ERRORS = {"trailing comma", "extra whitespace"}

# Custom exceptions for better error categorization
class ParserError(Exception):
    """Base exception for parser errors."""
    pass

class GeminiTimeoutError(ParserError):
    """Gemini HTTP request timed out."""
    pass

class GeminiJsonError(ParserError):
    """Gemini response JSON was malformed after all recovery attempts."""
    pass

class GeminiNetworkError(ParserError):
    """Network-level error communicating with Gemini."""
    pass

class GeminiPermanentError(ParserError):
    """Permanent error from Gemini (safety, recitation, etc.)."""
    pass

class ParserCancelledError(ParserError):
    """Parser was cancelled via cancellation_check."""
    pass

class ParserTimeoutError(ParserError):
    """Parser exceeded global or per-page timeout."""
    pass

class VlmQuotaExhaustedError(RuntimeError):
    pass

class GeminiRateLimitError(RuntimeError):
    def __init__(self, message, retry_after=60.0):
        super().__init__(message)
        self.retry_after = retry_after


# ------------------------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------------------------
_vlm_quota_exhausted = False
_vlm_quota_lock = threading.Lock()

_gemini_rate_lock = threading.Lock()
_gemini_last_call_time = 0.0
GEMINI_MIN_INTERVAL_SECONDS = float(os.getenv("GEMINI_MIN_INTERVAL_SECONDS", "6.0"))
GEMINI_MODEL_NAME = "gemini-2.5-flash"
GEMINI_API_URL_TEMPLATE = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
)

SUPPORTED_TEXT_EXTENSIONS = {".txt"}
SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}
SUPPORTED_MULTIMODAL_EXTENSIONS = SUPPORTED_IMAGE_EXTENSIONS | {".pdf"}

DOCUMENT_GRAPH_PROMPT = """You are a document understanding engine.
Return ONLY valid JSON.
Do not include markdown, code fences, comments, explanations, or any extra text.

Extract a document graph from the page image.

Required JSON schema:
{
  "nodes": [
    {
      "structural_type": "header|heading|paragraph|footer|table|table_row|table_cell|list|list_item|figure|caption|metadata|reference|quote|code",
      "text": "...",
      "reading_order": 1,
      "semantic_category": "person|organization|identifier|date|location|title|heading|summary|metadata|body_text|reference|citation|concept|definition|procedure|relationship|event|measurement|table|figure|caption|financial_value|legal_reference|scientific_term",
      "entity_group": "entity_group_001|entity_group_002|entity_group_003...",
      "confidence": 0.95,
      "bbox": {
        "x1": 0.0,
        "y1": 0.0,
        "x2": 1.0,
        "y2": 1.0
      }
    }
  ]
}

Rules:
- Return normalized bounding boxes in the 0 to 1 range when possible.
- Use only the allowed structural types and semantic categories.
- For every text block assign an 'entity_group' id (blocks that belong to the same conceptual entity collection should share an entity_group id, e.g. entity_group_001, entity_group_002). Do NOT use domain-specific/document-specific labels for entity groups.
- Preserve the visual reading order.
- Keep text verbatim where possible.
- If the page is blank, return an empty nodes array.
- The response must be a single JSON object.
- Do NOT transcribe horizontal dividing lines, borders, or page separators (such as long sequences of dashes, hyphens, underscores, or dots). Omit them entirely from the text.
"""

# Allowed structural types as defined in the prompt
ALLOWED_STRUCTURAL_TYPES = {
    "header", "heading", "paragraph", "footer", "table", "table_row", "table_cell",
    "list", "list_item", "figure", "caption", "metadata", "reference", "quote", "code"
}

ALLOWED_SEMANTIC_CATEGORIES = {
    "person", "organization", "identifier", "date", "location", "title", "heading",
    "summary", "metadata", "body_text", "reference", "citation", "concept", "definition",
    "procedure", "relationship", "event", "measurement", "table", "figure", "caption",
    "financial_value", "legal_reference", "scientific_term"
}

def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))

def _trace(trace_fn: Optional[Callable[[str], None]], message: str) -> None:
    logger.info(message)
    if trace_fn is None:
        return
    try:
        trace_fn(message)
    except Exception:
        pass

def _is_text_file(file_path: str) -> bool:
    return os.path.splitext(file_path)[1].lower() in SUPPORTED_TEXT_EXTENSIONS

def _is_image_file(file_path: str) -> bool:
    return os.path.splitext(file_path)[1].lower() in SUPPORTED_IMAGE_EXTENSIONS

def _is_pdf_file(file_path: str) -> bool:
    return os.path.splitext(file_path)[1].lower() == ".pdf"

def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        number = float(value)
        if math.isnan(number) or math.isinf(number):
            return default
        return number
    except Exception:
        return default

def _document_extension(file_path: str) -> str:
    return os.path.splitext(file_path)[1].lower()

def _get_gemini_api_key() -> str:
    candidates = [
        os.getenv("GEMINI_API_KEY"),
        os.getenv("GOOGLE_API_KEY"),
        getattr(config, "GEMINI_API_KEY", None),
        getattr(config, "GOOGLE_API_KEY", None),
    ]
    for candidate in candidates:
        if candidate:
            return str(candidate).strip()
    return ""

def _gemini_throttle() -> None:
    global _gemini_last_call_time
    with _gemini_rate_lock:
        now = time.monotonic()
        elapsed = now - _gemini_last_call_time
        wait_seconds = GEMINI_MIN_INTERVAL_SECONDS - elapsed
        if wait_seconds > 0:
            time.sleep(wait_seconds)
        _gemini_last_call_time = time.monotonic()

def _check_memory_before_render(pages_to_render: int, target_dpi: int) -> None:
    pages_to_render = max(1, int(pages_to_render))
    target_dpi = max(72, int(target_dpi))
    estimated_mb = pages_to_render * 25.0 * (target_dpi / 300.0) ** 2
    available_mb = psutil.virtual_memory().available / (1024.0 * 1024.0)
    if estimated_mb > available_mb * 0.70:
        raise MemoryError(
            f"Preprocess render requires approximately {estimated_mb:.0f} MB, which exceeds the safe memory budget"
        )

def analyze_image_spatial_quality(image_np: np.ndarray) -> Tuple[float, float, float]:
    if image_np is None or image_np.size == 0:
        return 0.0, 0.0, 0.0
    if image_np.ndim == 3 and image_np.shape[2] == 4:
        gray = cv2.cvtColor(image_np, cv2.COLOR_BGRA2GRAY)
    elif image_np.ndim == 3:
        gray = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)
    else:
        gray = image_np.astype(np.uint8, copy=False)
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    contrast_score = float(np.std(gray))
    edges = cv2.Canny(gray, 50, 150)
    edge_density = float((np.count_nonzero(edges) / float(gray.size)) * 100.0)
    return blur_score, contrast_score, edge_density

def _score_text_coherence(text: str) -> float:
    if not text or len(text.strip()) < 20:
        return 0.0

    lines = [line for line in text.splitlines() if line.strip()]
    tokens = re.findall(r"[A-Za-z0-9']+", text)
    alpha_tokens = [token for token in tokens if any(char.isalpha() for char in token)]
    total_non_space = len(re.sub(r"\s", "", text)) or 1

    if not alpha_tokens:
        return 0.0

    alpha_chars = sum(sum(1 for char in token if char.isalpha()) for token in alpha_tokens)
    alpha_ratio = alpha_chars / total_non_space
    average_word_length = sum(len(token) for token in alpha_tokens) / max(len(alpha_tokens), 1)
    content_lines = 0
    for line in lines:
        if len(re.findall(r"[A-Za-z]{2,}", line)) >= 2:
            content_lines += 1
    line_coherence = content_lines / max(len(lines), 1)
    token_count_factor = min(1.0, len(alpha_tokens) / 60.0)

    base = 0.0
    base += _clamp(alpha_ratio / 0.58) * 32.0
    base += _clamp(1.0 - abs(average_word_length - 6.0) / 7.0) * 20.0
    base += _clamp(line_coherence) * 28.0
    base += token_count_factor * 20.0

    replacement_penalty = 1.0 - min(0.75, text.count("\ufffd") / max(len(text), 1) * 12.0)
    digit_alpha_mixture = sum(1 for token in alpha_tokens if re.search(r"[A-Za-z]\d|\d[A-Za-z]", token))
    if alpha_tokens:
        replacement_penalty *= 1.0 - min(0.35, (digit_alpha_mixture / len(alpha_tokens)) * 1.2)

    return round(max(0.0, min(100.0, base * replacement_penalty)), 1)

@dataclass
class PreprocessingReport:
    document_type: str = "MULTIMODAL"
    routing_action: str = "VLM_GRAPH_ROUTE"
    parse_method_hint: str = "vlm_document_graph"
    requires_vlm: bool = True
    document_graph_enabled: bool = True
    graph_schema_version: str = "1.0"
    extractable_text_ratio: float = 0.0
    average_blur_score: float = 0.0
    average_contrast_score: float = 0.0
    average_edge_density: float = 0.0
    handwritten_confidence: float = 0.0
    needs_enhancement: bool = False
    used_enhancement: bool = False
    enhancement_flags: Dict[str, Any] = field(default_factory=dict)
    timings: Dict[str, float] = field(default_factory=dict)
    hard_reject: bool = False
    reject_reason: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    overall_quality_score: float = 0.0
    overall_quality: float = 0.0
    routing_confidence: float = 0.0
    enhanced_pages_path: Optional[str] = None
    quality_scores: Dict[str, float] = field(
        default_factory=lambda: {
            "blur": 0.0,
            "contrast": 0.0,
            "edge_density": 0.0,
            "handwritten_confidence": 0.0,
            "coherence": 0.0,
        }
    )
    is_encrypted: bool = False
    is_corrupted: bool = False

def _ensure_pil_image(image: Any) -> Any:
    if PIL_AVAILABLE and isinstance(image, Image.Image):
        return image
    if isinstance(image, np.ndarray):
        if not PIL_AVAILABLE:
            raise RuntimeError("PIL is not available")
        if image.ndim == 2:
            return Image.fromarray(image.astype(np.uint8), mode="L").convert("RGB")
        if image.ndim == 3 and image.shape[2] == 4:
            return Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGRA2RGB))
        if image.ndim == 3:
            return Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    raise TypeError(f"Unsupported image type: {type(image)!r}")

def _pil_to_base64(image: Any) -> str:
    pil_image = _ensure_pil_image(image)
    buffer = io.BytesIO()
    if pil_image.mode not in ("RGB", "L"):
        pil_image = pil_image.convert("RGB")
    pil_image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")

def _clean_json_text(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()

def _extract_gemini_text(response_json: Dict[str, Any]) -> str:
    candidates = response_json.get("candidates") or []
    for candidate in candidates:
        content = candidate.get("content") or {}
        parts = content.get("parts") or []
        texts: List[str] = []
        for part in parts:
            part_text = part.get("text")
            if isinstance(part_text, str) and part_text.strip():
                texts.append(part_text)
        if texts:
            return "\n".join(texts)
    if isinstance(response_json.get("text"), str):
        return response_json["text"]
    return ""

def _normalize_bbox(raw_bbox: Any, image_width: int, image_height: int) -> Dict[str, float]:
    if isinstance(raw_bbox, dict):
        x1 = _safe_float(raw_bbox.get("x1", raw_bbox.get("left", 0.0)))
        y1 = _safe_float(raw_bbox.get("y1", raw_bbox.get("top", 0.0)))
        x2 = _safe_float(raw_bbox.get("x2", raw_bbox.get("right", 1.0)))
        y2 = _safe_float(raw_bbox.get("y2", raw_bbox.get("bottom", 1.0)))
    elif isinstance(raw_bbox, (list, tuple)) and len(raw_bbox) >= 4:
        x1 = _safe_float(raw_bbox[0])
        y1 = _safe_float(raw_bbox[1])
        x2 = _safe_float(raw_bbox[2])
        y2 = _safe_float(raw_bbox[3])
    else:
        x1, y1, x2, y2 = 0.0, 0.0, 1.0, 1.0

    if max(abs(x1), abs(y1), abs(x2), abs(y2)) > 1.5 and image_width > 0 and image_height > 0:
        x1 = x1 / float(image_width)
        x2 = x2 / float(image_width)
        y1 = y1 / float(image_height)
        y2 = y2 / float(image_height)

    x1, x2 = sorted((_clamp(x1), _clamp(x2)))
    y1, y2 = sorted((_clamp(y1), _clamp(y2)))
    return {"x1": round(x1, 6), "y1": round(y1, 6), "x2": round(x2, 6), "y2": round(y2, 6)}

def _normalize_node_type(node_type: Any) -> str:
    # Map any value not in allowed set to "paragraph"
    value = str(node_type or "paragraph").strip().lower()
    return value if value in ALLOWED_STRUCTURAL_TYPES else "paragraph"

def _normalize_semantic_category(category: Any) -> str:
    value = str(category or "body_text").strip().lower()
    return value if value in ALLOWED_SEMANTIC_CATEGORIES else "body_text"

def _estimate_handwritten_confidence(blur_score: float, contrast_score: float, edge_density: float) -> float:
    blur_component = _clamp((200.0 - blur_score) / 200.0)
    contrast_component = _clamp((65.0 - contrast_score) / 65.0)
    edge_component = _clamp(edge_density / 8.0)
    score = (blur_component * 0.25) + (contrast_component * 0.45) + (edge_component * 0.30)
    return round(_clamp(score), 3)

def _normalize_quality_scores(
    blur_score: float,
    contrast_score: float,
    edge_density: float,
    handwritten_confidence: float,
    coherence_score: float,
) -> Dict[str, float]:
    blur_quality = 100.0 * (1.0 - math.exp(-max(0.0, blur_score) / 180.0))
    contrast_quality = 100.0 * (1.0 - math.exp(-max(0.0, contrast_score) / 35.0))
    edge_quality = 100.0 * math.exp(-((edge_density - 3.0) ** 2) / (2.0 * 3.5 ** 2))
    handwriting_quality = 100.0 * (1.0 - handwritten_confidence)
    overall = (blur_quality + contrast_quality + edge_quality + handwriting_quality + coherence_score) / 5.0
    return {
        "blur": round(_clamp(blur_quality, 0.0, 100.0), 2),
        "contrast": round(_clamp(contrast_quality, 0.0, 100.0), 2),
        "edge_density": round(_clamp(edge_quality, 0.0, 100.0), 2),
        "handwritten_confidence": round(_clamp(handwritten_confidence, 0.0, 1.0), 3),
        "coherence": round(_clamp(coherence_score, 0.0, 100.0), 2),
        "overall": round(_clamp(overall, 0.0, 100.0), 2),
    }

def _enhance_numpy_image(image_np: np.ndarray) -> np.ndarray:
    if image_np.ndim == 2:
        bgr = cv2.cvtColor(image_np, cv2.COLOR_GRAY2BGR)
    elif image_np.ndim == 3 and image_np.shape[2] == 4:
        bgr = cv2.cvtColor(image_np, cv2.COLOR_BGRA2BGR)
    else:
        bgr = image_np.copy()

    if getattr(config, "PREPROCESS_ENABLE_DENOISE", False):
        bgr = cv2.fastNlMeansDenoisingColored(bgr, None, 6, 6, 7, 21)

    if getattr(config, "PREPROCESS_ENABLE_SHARPEN", False):
        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32)
        bgr = cv2.filter2D(bgr, -1, kernel)

    return bgr

def _page_to_image_metadata(image: Any, page_number: int) -> Dict[str, Any]:
    pil_image = _ensure_pil_image(image)
    width, height = pil_image.size
    return {
        "page_number": page_number,
        "width": width,
        "height": height,
        "mode": pil_image.mode,
    }

def _generate_spatial_edges(nodes: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], bool]:
    """
    Build spatial relationships between nodes using bounding box overlap and relative positions.
    Returns a tuple of (edges, is_truncated).
    """
    edges = []
    is_truncated = False
    if len(nodes) < 2:
        return edges, is_truncated

    # Pre-extract boxes
    node_data = []
    for node in nodes:
        bbox = node.get("bbox", {})
        x1 = _safe_float(bbox.get("x1", 0))
        y1 = _safe_float(bbox.get("y1", 0))
        x2 = _safe_float(bbox.get("x2", 1))
        y2 = _safe_float(bbox.get("y2", 1))
        node_data.append((node["chunk_id"], x1, y1, x2, y2))

    VERTICAL_THRESHOLD = 0.10
    HORIZONTAL_THRESHOLD = 0.10
    MAX_GRAPH_EDGES_LOCAL = MAX_GRAPH_EDGES

    n = len(node_data)
    for i in range(n):
        id_i, x1_i, y1_i, x2_i, y2_i = node_data[i]
        area_i = max(0.0, (x2_i - x1_i) * (y2_i - y1_i))
        for j in range(i + 1, n):
            id_j, x1_j, y1_j, x2_j, y2_j = node_data[j]
            # Intersection
            ix1 = max(x1_i, x1_j)
            iy1 = max(y1_i, y1_j)
            ix2 = min(x2_i, x2_j)
            iy2 = min(y2_i, y2_j)
            inter_area = max(0.0, (ix2 - ix1)) * max(0.0, (iy2 - iy1))
            area_j = max(0.0, (x2_j - x1_j) * (y2_j - y1_j))

            # INSIDE: if one node is mostly contained by another
            if area_i > 0 and inter_area / area_i > 0.9:
                edges.append({"from": id_i, "to": id_j, "relation": "INSIDE"})
                continue
            if area_j > 0 and inter_area / area_j > 0.9:
                edges.append({"from": id_j, "to": id_i, "relation": "INSIDE"})
                continue

            # Determine relative position
            center_i_y = (y1_i + y2_i) / 2.0
            center_i_x = (x1_i + x2_i) / 2.0
            center_j_y = (y1_j + y2_j) / 2.0
            center_j_x = (x1_j + x2_j) / 2.0

            # Vertical relationship with proximity threshold (0.10)
            if y2_i <= y1_j and (y1_j - y2_i) < VERTICAL_THRESHOLD:
                edges.append({"from": id_i, "to": id_j, "relation": "ABOVE"})
            elif y2_j <= y1_i and (y1_i - y2_j) < VERTICAL_THRESHOLD:
                edges.append({"from": id_j, "to": id_i, "relation": "ABOVE"})
            # Horizontal relationship with proximity threshold (0.10)
            elif x2_i <= x1_j and (x1_j - x2_i) < HORIZONTAL_THRESHOLD:
                edges.append({"from": id_i, "to": id_j, "relation": "LEFT_OF"})
            elif x2_j <= x1_i and (x1_i - x2_j) < HORIZONTAL_THRESHOLD:
                edges.append({"from": id_j, "to": id_i, "relation": "LEFT_OF"})

    # Hard edge cap to prevent memory/performance degradation
    if len(edges) > MAX_GRAPH_EDGES_LOCAL:
        logger.warning(
            f"Graph edge explosion: {len(edges)} edges; truncating to {MAX_GRAPH_EDGES_LOCAL}"
        )
        edges = edges[:MAX_GRAPH_EDGES_LOCAL]
        is_truncated = True

    return edges, is_truncated


class DocumentPreprocessor:
    def __init__(self, file_path: str):
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        self.file_path = os.path.abspath(file_path)
        self.filename = os.path.basename(self.file_path)

    def _read_text_file(self) -> str:
        with open(self.file_path, "r", encoding="utf-8", errors="ignore") as handle:
            return handle.read()

    def _pdf_reader(self) -> pypdf.PdfReader:
        return pypdf.PdfReader(self.file_path)

    def _pdf_page_count(self) -> int:
        reader = self._pdf_reader()
        return len(reader.pages)

    def _validate_pdf_structure(self, report: PreprocessingReport, trace_fn: Optional[Callable[[str], None]] = None) -> int:
        try:
            reader = self._pdf_reader()
            if reader.is_encrypted:
                report.is_encrypted = True
                decrypt_result = 0
                try:
                    decrypt_result = reader.decrypt("")
                except Exception:
                    decrypt_result = 0
                if decrypt_result == 0:
                    report.is_encrypted = True
                    report.warnings.append("Encrypted PDF routed to VLM")
                    return len(reader.pages)
                report.warnings.append("PDF is encrypted but blank-password decryption succeeded")

            page_count = len(reader.pages)
            if page_count <= 0:
                report.is_corrupted = True
                report.hard_reject = True
                report.reject_reason = "PDF contains no pages"
                report.warnings.append("PDF has zero pages")
                return 0

            if page_count > getattr(config, "PDF_MAX_PAGES", 600):
                report.warnings.append(
                    f"PDF page count {page_count} exceeds configured limit {getattr(config, 'PDF_MAX_PAGES', 600)}"
                )

            return page_count
        except Exception as exc:
            report.is_corrupted = True
            report.hard_reject = True
            report.reject_reason = f"PDF structural validation failed: {exc}"
            report.warnings.append(str(exc))
            _trace(trace_fn, f"[PREPROCESS] PDF validation failed: {exc}")
            return 0

    def _render_image_frames(
        self,
        max_pages: Optional[int] = None,
        trace_fn: Optional[Callable[[str], None]] = None,
    ) -> List[Any]:
        if not PIL_AVAILABLE:
            raise RuntimeError("PIL is required to render image files")

        images: List[Any] = []
        with Image.open(self.file_path) as source:
            frame_count = int(getattr(source, "n_frames", 1) or 1)
            limit = frame_count if max_pages is None else min(frame_count, max_pages)
            _check_memory_before_render(limit, getattr(config, "PREPROCESS_TARGET_DPI", 300))
            for frame_index in range(limit):
                try:
                    source.seek(frame_index)
                    frame = source.convert("RGB").copy()
                    images.append(frame)
                except EOFError:
                    break
        if not images:
            raise RuntimeError("No image frames could be rendered")
        _trace(trace_fn, f"[PREPROCESS] Rendered {len(images)} image frame(s)")
        return images

    def _render_pdf_pages(
        self,
        max_pages: Optional[int] = None,
        dpi: Optional[int] = None,
        trace_fn: Optional[Callable[[str], None]] = None,
    ) -> List[Any]:
        if not PDF2IMAGE_AVAILABLE or convert_from_path is None:
            raise RuntimeError("pdf2image is required to render PDF documents")

        page_count = self._pdf_page_count()
        limit = page_count if max_pages is None else min(page_count, max_pages)
        if limit <= 0:
            raise RuntimeError("PDF contains no pages to render")

        target_dpi = int(dpi or getattr(config, "PREPROCESS_TARGET_DPI", 300))
        _check_memory_before_render(limit, target_dpi)
        poppler_path = getattr(config, "PREPROCESS_POPPLER_PATH", "") or os.getenv("PREPROCESS_POPPLER_PATH", "") or None
        images = convert_from_path(
            self.file_path,
            first_page=1,
            last_page=limit,
            dpi=target_dpi,
            poppler_path=poppler_path,
        )
        rendered_images = [image.convert("RGB") if getattr(image, "mode", None) != "RGB" else image for image in images]
        if not rendered_images:
            raise RuntimeError("PDF rendering produced no images")
        _trace(trace_fn, f"[PREPROCESS] Rendered {len(rendered_images)} PDF page(s) at {target_dpi} DPI")
        return rendered_images

    def _render_pages(
        self,
        max_pages: Optional[int] = None,
        dpi: Optional[int] = None,
        trace_fn: Optional[Callable[[str], None]] = None,
    ) -> List[Any]:
        if _is_pdf_file(self.file_path):
            return self._render_pdf_pages(max_pages=max_pages, dpi=dpi, trace_fn=trace_fn)
        if _is_image_file(self.file_path):
            return self._render_image_frames(max_pages=max_pages, trace_fn=trace_fn)
        if _is_text_file(self.file_path):
            raise ValueError("Text files are not rendered as images")

        if PIL_AVAILABLE:
            try:
                return self._render_image_frames(max_pages=max_pages, trace_fn=trace_fn)
            except Exception as exc:
                _trace(trace_fn, f"[PREPROCESS] Generic image render failed: {exc}")
        raise RuntimeError("Unsupported document format for image rendering")

    def _render_sample_pages(self, trace_fn: Optional[Callable[[str], None]] = None) -> List[Any]:
        sample_pages = max(1, int(getattr(config, "PREPROCESS_SAMPLE_PAGES", 5)))
        _trace(trace_fn, f"[PREPROCESS] Rendering sample pages: limit={sample_pages}")
        return self._render_pages(max_pages=sample_pages, dpi=getattr(config, "PREPROCESS_TARGET_DPI", 300), trace_fn=trace_fn)

    def render_document(
        self,
        max_pages: Optional[int] = None,
        dpi: Optional[int] = None,
        trace_fn: Optional[Callable[[str], None]] = None,
    ) -> List[Any]:
        return self._render_pages(max_pages=max_pages, dpi=dpi, trace_fn=trace_fn)

    def _compute_image_report_metrics(self, images: Sequence[Any]) -> Tuple[float, float, float, float, Dict[str, float]]:
        blur_scores: List[float] = []
        contrast_scores: List[float] = []
        edge_scores: List[float] = []
        handwritten_scores: List[float] = []

        for image in images:
            pil_image = _ensure_pil_image(image)
            image_np = np.array(pil_image.convert("RGB"))
            blur_score, contrast_score, edge_density = analyze_image_spatial_quality(image_np)
            blur_scores.append(blur_score)
            contrast_scores.append(contrast_score)
            edge_scores.append(edge_density)
            handwritten_scores.append(_estimate_handwritten_confidence(blur_score, contrast_score, edge_density))

        average_blur = float(sum(blur_scores) / max(len(blur_scores), 1))
        average_contrast = float(sum(contrast_scores) / max(len(contrast_scores), 1))
        average_edge_density = float(sum(edge_scores) / max(len(edge_scores), 1))
        handwritten_confidence = float(sum(handwritten_scores) / max(len(handwritten_scores), 1))
        coherence = 0.0
        quality_scores = _normalize_quality_scores(
            average_blur,
            average_contrast,
            average_edge_density,
            handwritten_confidence,
            coherence,
        )
        return average_blur, average_contrast, average_edge_density, handwritten_confidence, quality_scores

    def generate_routing_report(self, trace_fn: Optional[Callable[[str], None]] = None) -> PreprocessingReport:
        started_at = time.perf_counter()
        report = PreprocessingReport()

        extension = _document_extension(self.file_path)
        report.enhancement_flags = {
            "file_extension": extension,
            "sample_pages": int(getattr(config, "PREPROCESS_SAMPLE_PAGES", 5)),
            "target_dpi": int(getattr(config, "PREPROCESS_TARGET_DPI", 300)),
        }

        if _is_text_file(self.file_path):
            report.document_type = "TEXT"
            report.routing_action = "DIRECT_PARSE"
            report.parse_method_hint = "plaintext"
            report.requires_vlm = False
            report.document_graph_enabled = False
            report.graph_schema_version = "1.0"
            try:
                text = self._read_text_file()
                coherence_score = _score_text_coherence(text)
                report.extractable_text_ratio = 1.0 if text.strip() else 0.0
                report.overall_quality_score = coherence_score
                report.overall_quality = coherence_score
                report.routing_confidence = 1.0
                report.quality_scores = _normalize_quality_scores(0.0, 0.0, 0.0, 0.0, coherence_score)
            except Exception as exc:
                report.hard_reject = True
                report.is_corrupted = True
                report.reject_reason = f"Text file read failed: {exc}"
                report.warnings.append(str(exc))
                report.routing_confidence = 0.0
            report.timings["total_preprocess_secs"] = round(time.perf_counter() - started_at, 3)
            return report

        report.document_type = "MULTIMODAL"
        report.routing_action = "VLM_GRAPH_ROUTE"
        report.parse_method_hint = "vlm_document_graph"
        report.requires_vlm = True
        report.document_graph_enabled = True
        report.graph_schema_version = "1.0"

        page_count = 0
        if _is_pdf_file(self.file_path):
            page_count = self._validate_pdf_structure(report, trace_fn=trace_fn)
            if report.hard_reject:
                report.timings["total_preprocess_secs"] = round(time.perf_counter() - started_at, 3)
                report.overall_quality_score = 0.0
                report.overall_quality = 0.0
                report.routing_confidence = 0.0
                return report

        try:
            sample_images = self._render_sample_pages(trace_fn=trace_fn)
            (
                report.average_blur_score,
                report.average_contrast_score,
                report.average_edge_density,
                report.handwritten_confidence,
                report.quality_scores,
            ) = self._compute_image_report_metrics(sample_images)

            if page_count <= 0:
                page_count = len(sample_images)

            if _is_pdf_file(self.file_path):
                report.extractable_text_ratio = 0.0
            else:
                report.extractable_text_ratio = 0.0

            coherence_score = 0.0
            report.overall_quality_score = report.quality_scores.get("overall", 0.0)
            report.overall_quality = report.overall_quality_score
            report.routing_confidence = round(_clamp(report.overall_quality_score / 100.0, 0.5, 0.99), 3)

            low_blur = report.average_blur_score < getattr(config, "PREPROCESS_BLUR_MIN", 40.0)
            low_contrast = report.average_contrast_score < getattr(config, "PREPROCESS_CONTRAST_MIN", 35.0)
            low_edge_density = report.average_edge_density < 0.25
            handwritten = report.handwritten_confidence >= getattr(config, "PREPROCESS_HW_SCORE_MIN", 0.70)

            report.needs_enhancement = bool(low_blur or low_contrast or low_edge_density or handwritten)
            if report.needs_enhancement:
                reasons: List[str] = []
                if low_blur:
                    reasons.append(f"low blur score {report.average_blur_score:.1f}")
                if low_contrast:
                    reasons.append(f"low contrast score {report.average_contrast_score:.1f}")
                if low_edge_density:
                    reasons.append(f"low edge density {report.average_edge_density:.2f}")
                if handwritten:
                    reasons.append(f"handwritten confidence {report.handwritten_confidence:.2f}")
                report.enhancement_flags["reasons"] = reasons
            else:
                report.enhancement_flags["reasons"] = []

            report.enhancement_flags["page_count"] = page_count
            report.enhancement_flags["render_sample_pages"] = len(sample_images)
            report.enhancement_flags["document_kind"] = "pdf" if _is_pdf_file(self.file_path) else "image"
            report.enhancement_flags["coherence_score"] = coherence_score
        except Exception as exc:
            report.warnings.append(f"Sample rendering failed: {exc}")
            report.hard_reject = True
            report.is_corrupted = True
            report.reject_reason = f"Unable to render document pages: {exc}"
            report.routing_confidence = 0.0
            report.overall_quality_score = 0.0
            report.overall_quality = 0.0
            report.needs_enhancement = False

        if report.hard_reject:
            report.timings["total_preprocess_secs"] = round(time.perf_counter() - started_at, 3)
            return report

        report.timings["total_preprocess_secs"] = round(time.perf_counter() - started_at, 3)
        return report


# ------------------------------------------------------------------------------
# Gemini page parser with enhanced retry, timeouts, and cancellation
# ------------------------------------------------------------------------------
def _call_gemini_page_parser(
    image: Any,
    page_number: Optional[int] = None,
    pipeline_id: Optional[str] = None,
    timeout_seconds: int = 300,
    retries: int = 4,
    trace_fn: Optional[Callable[[str], None]] = None,
    cancellation_check: Optional[Callable[[], bool]] = None,
    timeout_check: Optional[Callable[[], bool]] = None,
    page_start_time: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Call Gemini API to parse a page with bounded retries and timeouts.
    Returns a validated and normalized JSON dict (the page graph data).
    Raises specific exceptions for different failure modes.
    """
    api_key = _get_gemini_api_key()
    if not api_key:
        raise RuntimeError("Gemini API key is not configured")

    # Check cancellation before any work
    if cancellation_check and cancellation_check():
        raise ParserCancelledError(f"Cancelled before Gemini call for page {page_number}")

    # Per-page timeout check (using page_start_time for total duration)
    if page_start_time is not None and timeout_check and timeout_check():
        raise ParserTimeoutError(f"Global timeout exceeded before Gemini call for page {page_number}")

    pil_image = _ensure_pil_image(image)

    # Resize if too large to avoid payload issues
    max_dim = 1800
    width, height = pil_image.size
    if max(width, height) > max_dim:
        scale = max_dim / max(width, height)
        new_width = int(width * scale)
        new_height = int(height * scale)
        pil_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.LANCZOS)

    encoded_image = _pil_to_base64(pil_image)
    mime_type = "image/png"
    prompt = DOCUMENT_GRAPH_PROMPT
    if page_number is not None:
        prompt = f"Page number: {page_number}\nPipeline ID: {pipeline_id or ''}\n\n{DOCUMENT_GRAPH_PROMPT}"

    body = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": mime_type, "data": encoded_image}},
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0.0,
            "topP": 0.95,
            "maxOutputTokens": 32768,
            "responseMimeType": "application/json",
            "thinkingConfig": {
                "thinkingBudget": 0
            }
        },
    }
    url = GEMINI_API_URL_TEMPLATE.format(model=GEMINI_MODEL_NAME, api_key=api_key)
    headers = {"Content-Type": "application/json"}

    last_exception: Optional[BaseException] = None
    from services.gemini_rate_manager import GeminiRateManager
    rate_mgr = GeminiRateManager()

    # Max total retry duration is bounded by page_start_time and MAX_RETRY_DURATION_SECONDS
    max_total_retry_duration = min(MAX_RETRY_DURATION_SECONDS, timeout_seconds)

    for attempt in range(max(1, retries)):
        # Check cancellation before each attempt
        if cancellation_check and cancellation_check():
            raise ParserCancelledError(f"Cancelled before Gemini attempt {attempt+1} for page {page_number}")
        if timeout_check and timeout_check():
            raise ParserTimeoutError(f"Global timeout exceeded during Gemini attempt {attempt+1} for page {page_number}")
        if page_start_time is not None and (time.time() - page_start_time) > max_total_retry_duration:
            raise ParserTimeoutError(f"Page retry duration exceeded for page {page_number} after {time.time() - page_start_time:.1f}s")

        raw_text = ""
        cleaned = ""
        try:
            # Throttle per API limits
            rate_mgr.wait_if_needed(trace_fn)
            _gemini_throttle()

            # Use timeout tuple (connect, read)
            response = requests.post(
                url,
                headers=headers,
                json=body,
                timeout=(HTTP_CONNECT_TIMEOUT, HTTP_READ_TIMEOUT)
            )
            if response.status_code == 429:
                err_text = response.text
                retry_after_hdr = response.headers.get("Retry-After")
                wait_sec = rate_mgr.register_429(retry_after_hdr)
                is_quota = any(x in err_text.lower() for x in ["quota", "limit", "resource_exhausted", "exceeded"])
                if is_quota:
                    raise GeminiRateLimitError(f"Gemini returned HTTP 429 Quota/Resource Exhausted: {err_text[:500]}", retry_after=wait_sec)
                raise GeminiRateLimitError(f"Gemini returned HTTP 429 Rate Limit: {err_text[:500]}", retry_after=wait_sec)
            if response.status_code >= 500:
                # Transient server error; retry
                raise GeminiNetworkError(f"Gemini returned HTTP {response.status_code}: {response.text[:500]}")
            response.raise_for_status()
            rate_mgr.register_success()
            response_json = response.json()
            raw_text = _extract_gemini_text(response_json)

            # Check finish reason
            candidates = response_json.get("candidates", [])
            if candidates:
                finish_reason = candidates[0].get("finishReason")
                if finish_reason is not None:
                    if finish_reason == "STOP":
                        # Normal completion
                        pass
                    elif finish_reason == "MAX_TOKENS":
                        # Recoverable: retry with lower output? For now, treat as success but log warning.
                        logger.warning(f"Gemini finishReason=MAX_TOKENS for page {page_number}; output truncated.")
                    elif finish_reason in ("SAFETY", "RECITATION", "OTHER"):
                        raise GeminiPermanentError(f"Gemini blocked: finishReason={finish_reason} for page {page_number}")
                    else:
                        # Unknown reason, treat as permanent
                        raise GeminiPermanentError(f"Gemini finishReason={finish_reason} for page {page_number}")
                else:
                    logger.warning(f"Gemini response missing finishReason for page {page_number}")

            # Clean and parse JSON
            cleaned = _clean_json_text(raw_text)
            # Attempt to parse to validate
            try:
                json.loads(cleaned)
            except json.JSONDecodeError as e:
                # Try to repair common issues: remove trailing commas, extra whitespace, and balance braces
                repaired = _repair_json(cleaned)
                if repaired != cleaned:
                    try:
                        json.loads(repaired)
                        cleaned = repaired
                        logger.info(f"Repaired JSON for page {page_number}")
                    except json.JSONDecodeError:
                        # Still invalid; check if it's a recoverable error (like schema violation)
                        error_msg = str(e).lower()
                        if any(kw in error_msg for kw in RECOVERABLE_JSON_ERRORS):
                            # Recoverable, will retry
                            raise GeminiJsonError(f"JSON decode error after repair (recoverable) for page {page_number}: {e}")
                        else:
                            # Permanent schema violation
                            raise GeminiPermanentError(f"JSON schema violation for page {page_number}: {e}")
                else:
                    # Not repairable, check error type
                    error_msg = str(e).lower()
                    if any(kw in error_msg for kw in RECOVERABLE_JSON_ERRORS):
                        raise GeminiJsonError(f"JSON decode error (recoverable) for page {page_number}: {e}")
                    else:
                        raise GeminiPermanentError(f"JSON decode error (permanent) for page {page_number}: {e}")

            if not cleaned:
                raise GeminiJsonError(f"Gemini response did not contain JSON text for page {page_number}")

            # Validate and normalize schema in one pass, returning the normalized dict
            graph_data = _validate_and_normalize_json_schema(cleaned, page_number, image)

            # Free large objects
            del encoded_image, body, response_json, raw_text

            return graph_data

        except (requests.Timeout, requests.ConnectionError) as e:
            last_exception = GeminiTimeoutError(f"Network timeout/error for page {page_number}: {e}")
            # Continue to retry
        except (GeminiRateLimitError, GeminiNetworkError, GeminiJsonError, GeminiPermanentError) as e:
            # Specific Gemini errors
            if isinstance(e, GeminiPermanentError):
                # Permanent, don't retry
                raise e
            last_exception = e
            # For rate limit and network errors, we retry with backoff
        except Exception as e:
            # Unexpected error
            last_exception = e
            # We'll retry with backoff if transient
            if isinstance(e, requests.HTTPError) and e.response.status_code in (400, 403, 404):
                # Non-retryable client errors
                raise GeminiPermanentError(f"Gemini HTTP error {e.response.status_code}: {e.response.text[:200]}")
            # Other exceptions are considered retryable unless we run out of retries.
        finally:
            # Clean up large objects
            try:
                del encoded_image
            except Exception:
                pass
            try:
                del body
            except Exception:
                pass
            try:
                del response
            except Exception:
                pass
            try:
                del response_json
            except Exception:
                pass
            try:
                del raw_text
            except Exception:
                pass

        _trace(trace_fn, f"[VLM] Gemini page parser error on page {page_number} (attempt {attempt+1}/{retries}): {last_exception}")
        if attempt >= retries - 1:
            break
        # Exponential backoff with jitter
        backoff_seconds = min(20.0, (2.0 ** attempt) + (0.25 * attempt))
        time.sleep(backoff_seconds)

    # Raise the last specific exception if possible
    if last_exception:
        raise last_exception
    raise RuntimeError(f"Gemini page parser failed after {retries} attempts for page {page_number}")


def _validate_and_normalize_json_schema(json_text: str, page_number: int, image: Any) -> Dict[str, Any]:
    """
    Validate and normalize the JSON response against the expected schema.
    Returns the normalized data dict (ready for graph building).
    """
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as e:
        raise GeminiJsonError(f"Invalid JSON during schema validation: {e}")

    if not isinstance(data, dict):
        raise GeminiPermanentError(f"Response is not a dict for page {page_number}")

    nodes = data.get("nodes")
    if nodes is None:
        raise GeminiPermanentError(f"Missing 'nodes' field for page {page_number}")
    if not isinstance(nodes, list):
        raise GeminiPermanentError(f"'nodes' is not a list for page {page_number}")

    # Validate each node
    for idx, node in enumerate(nodes):
        if not isinstance(node, dict):
            raise GeminiPermanentError(f"Node {idx} is not a dict for page {page_number}")

        # Check required fields
        required_fields = ["text", "reading_order", "structural_type", "semantic_category", "entity_group", "confidence", "bbox"]
        for field in required_fields:
            if field not in node:
                raise GeminiPermanentError(f"Node {idx} missing required field '{field}' for page {page_number}")

        # Validate types and normalize values
        if not isinstance(node["text"], str):
            raise GeminiPermanentError(f"Node {idx} 'text' is not a string for page {page_number}")
        try:
            reading_order = int(node["reading_order"])
            if reading_order < 1:
                raise GeminiPermanentError(f"Node {idx} 'reading_order' must be positive")
        except (ValueError, TypeError):
            raise GeminiPermanentError(f"Node {idx} 'reading_order' is not an integer for page {page_number}")

        if not isinstance(node["confidence"], (int, float)):
            raise GeminiPermanentError(f"Node {idx} 'confidence' is not a number for page {page_number}")
        if not (0.0 <= float(node["confidence"]) <= 1.0):
            raise GeminiPermanentError(f"Node {idx} 'confidence' out of range for page {page_number}")

        # Normalize structural_type and semantic_category
        struct_type = str(node.get("structural_type", "paragraph")).strip().lower()
        node["structural_type"] = struct_type if struct_type in ALLOWED_STRUCTURAL_TYPES else "paragraph"
        sem_cat = str(node.get("semantic_category", "body_text")).strip().lower()
        node["semantic_category"] = sem_cat if sem_cat in ALLOWED_SEMANTIC_CATEGORIES else "body_text"

        # Validate bbox (will be normalized later)
        bbox = node.get("bbox")
        if not isinstance(bbox, dict):
            raise GeminiPermanentError(f"Node {idx} 'bbox' is not a dict for page {page_number}")
        for key in ["x1", "y1", "x2", "y2"]:
            if key not in bbox:
                raise GeminiPermanentError(f"Node {idx} 'bbox' missing '{key}' for page {page_number}")
            try:
                val = float(bbox[key])
                if val < 0 or val > 1:
                    # Warn but allow (normalization will clamp)
                    logger.warning(f"Node {idx} bbox {key}={val} out of [0,1] for page {page_number}")
            except (ValueError, TypeError):
                raise GeminiPermanentError(f"Node {idx} bbox '{key}' is not a number for page {page_number}")

    # Get image dimensions for bbox normalization
    pil_image = _ensure_pil_image(image)
    width, height = pil_image.size

    # Now build normalized nodes with bbox adjusted
    normalized_nodes: List[Dict[str, Any]] = []
    ordered_nodes: List[Tuple[int, Dict[str, Any]]] = []
    for idx, node in enumerate(nodes, start=1):
        raw_reading_order = node.get("reading_order", idx)
        try:
            reading_order = int(raw_reading_order)
        except Exception:
            reading_order = idx
        ordered_nodes.append((reading_order, node))

    ordered_nodes.sort(key=lambda item: (item[0],))

    for sequence_index, (_, node) in enumerate(ordered_nodes, start=1):
        bbox = node.get("bbox")
        # Normalize bbox
        norm_bbox = _normalize_bbox(bbox, width, height) if bbox else {"x1": 0.0, "y1": 0.0, "x2": 1.0, "y2": 1.0}
        normalized_nodes.append(
            {
                "chunk_id": f"p{page_number}_n{sequence_index}",
                "node_id": f"p{page_number}_n{sequence_index}",
                "type": node["structural_type"],
                "structural_type": node["structural_type"],
                "text": str(node.get("text", "") or "").strip(),
                "section": node["semantic_category"],
                "semantic_category": node["semantic_category"],
                "entity_group": str(node.get("entity_group", "unknown")).strip(),
                "confidence": float(node.get("confidence", 1.0)),
                "reading_order": sequence_index,
                "bbox": norm_bbox,
            }
        )

    # Generate edges: sequential NEXT and spatial relationships
    edges: List[Dict[str, Any]] = []
    for index in range(len(normalized_nodes) - 1):
        edges.append(
            {
                "from": normalized_nodes[index]["chunk_id"],
                "to": normalized_nodes[index + 1]["chunk_id"],
                "relation": "NEXT",
            }
        )
    # Add spatial edges
    spatial_edges, is_truncated = _generate_spatial_edges(normalized_nodes)
    edges.extend(spatial_edges)

    # Return the normalized page graph data
    return {
        "page_number": page_number,
        "source": "gemini",
        "width": width,
        "height": height,
        "nodes": normalized_nodes,
        "edges": edges,
        "status": "success",
        "metadata": {"graph_truncated": is_truncated},
    }


def _repair_json(text: str) -> str:
    """
    Attempt to repair common JSON issues, including:
    - trailing commas
    - surrounding garbage
    - missing closing braces/brackets (truncated JSON)
    """
    text = text.strip()
    # Remove trailing commas before closing braces/brackets
    text = re.sub(r',\s*}', '}', text)
    text = re.sub(r',\s*]', ']', text)
    # Remove leading/trailing garbage
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and start < end:
        text = text[start:end+1]
    else:
        # If no valid braces found, try to extract JSON-like structure
        # This is a fallback; we'll just return the cleaned text.
        pass

    # Attempt to balance braces: if the string appears truncated (e.g., ends with '[' or '{')
    # we try to add the necessary closing braces.
    open_braces = text.count('{') - text.count('}')
    open_brackets = text.count('[') - text.count(']')
    if open_braces > 0 or open_brackets > 0:
        # If there are unclosed braces, append missing closing braces.
        # This is a heuristic and may not always work, but can recover some truncations.
        if open_braces > 0:
            text += '}' * open_braces
        if open_brackets > 0:
            text += ']' * open_brackets

    return text


def _ocr_fallback_page(image: Any, page_number: int) -> Optional[Dict[str, Any]]:
    if not PYTESSERACT_AVAILABLE or pytesseract is None:
        return None

    def _recursive_xy_cut_layout(words, x_thresh=25, y_thresh=15):
        if not words:
            return []
        # Try horizontal projection cut (rows)
        words_sorted_y = sorted(words, key=lambda w: w["top"])
        h_groups = []
        current_group = [words_sorted_y[0]]
        for w in words_sorted_y[1:]:
            prev_bottom = max(x["top"] + x["height"] for x in current_group)
            if w["top"] - prev_bottom > y_thresh:
                h_groups.append(current_group)
                current_group = [w]
            else:
                current_group.append(w)
        h_groups.append(current_group)

        if len(h_groups) > 1:
            final_groups = []
            for g in h_groups:
                final_groups.extend(_recursive_xy_cut_layout(g, x_thresh, y_thresh))
            return final_groups

        # Vertical projection cut (columns)
        words_sorted_x = sorted(words, key=lambda w: w["left"])
        v_groups = []
        current_group_v = [words_sorted_x[0]]
        for w in words_sorted_x[1:]:
            prev_right = max(x["left"] + x["width"] for x in current_group_v)
            if w["left"] - prev_right > x_thresh:
                v_groups.append(current_group_v)
                current_group_v = [w]
            else:
                current_group_v.append(w)
        v_groups.append(current_group_v)

        if len(v_groups) > 1:
            final_groups = []
            for g in v_groups:
                final_groups.extend(_recursive_xy_cut_layout(g, x_thresh, y_thresh))
            return final_groups

        return [words]

    def _classify_ocr_block(text: str) -> tuple[str, str]:
        text_clean = text.strip()
        text_lower = text_clean.lower()
        if len(text_clean) < 100 and (text_clean.isupper() or any(p in text_lower for p in ["chapter", "section", "abstract", "summary", "introduction", "claims", "description"])):
            struct_type = "heading"
        elif "\n" in text_clean and ("|" in text_clean or "  " in text_clean):
            struct_type = "table"
        else:
            struct_type = "paragraph"

        if any(p in text_lower for p in ["filing date", "publication date", "date of"]):
            sem_cat = "date"
        elif any(p in text_lower for p in ["application no", "patent no", "invoice no", "no.", "number"]):
            sem_cat = "identifier"
        elif any(p in text_lower for p in ["inventor", "applicant", "author", "mr.", "ms.", "dr."]):
            sem_cat = "person"
        elif any(p in text_lower for p in ["university", "inc.", "corp.", "ltd.", "association"]):
            sem_cat = "organization"
        else:
            sem_cat = "body_text"

        return struct_type, sem_cat

    def _cluster_ocr_entity_groups(nodes):
        # Use a spatial grid to reduce comparisons.
        # Store (node, index) in grid to avoid O(n) list.index() lookup.
        cell_size = 0.05
        grid = {}
        for idx, node in enumerate(nodes):
            bbox = node["bbox"]
            cx = (bbox["x1"] + bbox["x2"]) / 2
            cy = (bbox["y1"] + bbox["y2"]) / 2
            cell = (int(cx / cell_size), int(cy / cell_size))
            grid.setdefault(cell, []).append((idx, node))

        entity_groups = {}
        visited = set()
        group_idx = 1

        for i, n1 in enumerate(nodes):
            if i in visited:
                continue
            group_id = f"entity_group_{group_idx:03d}"
            entity_groups[group_id] = [n1]
            visited.add(i)

            b1 = n1["bbox"]
            cx1 = (b1["x1"] + b1["x2"]) / 2
            cy1 = (b1["y1"] + b1["y2"]) / 2
            cell1 = (int(cx1 / cell_size), int(cy1 / cell_size))
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    cell = (cell1[0]+dx, cell1[1]+dy)
                    for j, n2 in grid.get(cell, []):
                        if j in visited:
                            continue
                        b2 = n2["bbox"]
                        v_gap = abs(b2["y1"] - b1["y2"])
                        h_overlap = not (b2["x2"] < b1["x1"] or b2["x1"] > b1["x2"])
                        if v_gap < 0.05 and h_overlap:
                            entity_groups[group_id].append(n2)
                            visited.add(j)
            group_idx += 1

        for grp_id, grp_nodes in entity_groups.items():
            for gn in grp_nodes:
                gn["entity_group"] = grp_id

    try:
        pil_image = _ensure_pil_image(image).convert("L")
        width, height = pil_image.size

        # Extract hOCR character data
        data = pytesseract.image_to_data(pil_image, output_type=Output.DICT, config="--oem 3 --psm 3")
        raw_words = []
        n_boxes = len(data['level'])
        for i in range(n_boxes):
            if data['level'][i] == 5:
                text = data['text'][i].strip()
                if not text:
                    continue
                conf = int(data['conf'][i]) if data['conf'][i] != '-1' else 0
                if conf < 20:
                    continue
                raw_words.append({
                    "text": text,
                    "left": data['left'][i],
                    "top": data['top'][i],
                    "width": data['width'][i],
                    "height": data['height'][i]
                })

        if not raw_words:
            return None

        # 1. Apply Recursive XY-Cut layouts
        word_groups = _recursive_xy_cut_layout(raw_words)

        nodes = []
        for idx, words in enumerate(word_groups):
            if not words:
                continue
            # Sort words inside group by reading flow
            sorted_words = sorted(words, key=lambda w: (w["top"], w["left"]))
            paragraph_text = " ".join([w["text"] for w in sorted_words])

            x1 = min(w["left"] for w in words)
            y1 = min(w["top"] for w in words)
            x2 = max(w["left"] + w["width"] for w in words)
            y2 = max(w["top"] + w["height"] for w in words)

            bbox = {
                "x1": x1 / width,
                "y1": y1 / height,
                "x2": x2 / width,
                "y2": y2 / height
            }

            struct_type, sem_cat = _classify_ocr_block(paragraph_text)

            nodes.append({
                "chunk_id": f"p{page_number}_ocr_para_{idx + 1}",
                "node_id": f"p{page_number}_ocr_para_{idx + 1}",
                "type": struct_type,
                "structural_type": struct_type,
                "text": paragraph_text,
                "section": sem_cat,
                "semantic_category": sem_cat,
                "entity_group": "unknown",
                "confidence": 0.85,
                "reading_order": idx + 1,
                "bbox": bbox
            })

        # 2. Cluster entity groups dynamically (using spatial grid with index)
        _cluster_ocr_entity_groups(nodes)

        # 3. Build graph edges
        nodes.sort(key=lambda n: n["reading_order"])
        spatial_edges, is_truncated = _generate_spatial_edges(nodes)
        seq_edges = []
        for idx in range(len(nodes) - 1):
            seq_edges.append({
                "from": nodes[idx]["chunk_id"],
                "to": nodes[idx + 1]["chunk_id"],
                "relation": "NEXT"
            })
        all_edges = seq_edges + spatial_edges

        page_graph = {
            "page_number": page_number,
            "source": "ocr",
            "width": width,
            "height": height,
            "nodes": nodes,
            "edges": all_edges,
            "status": "ocr_fallback",
            "metadata": {"graph_truncated": is_truncated},
        }
        return page_graph
    except Exception as exc:
        logger.exception("[VLM] OCR fallback failed for page %s: %s", page_number, exc)
        return None


# ------------------------------------------------------------------------------
# Main VLM orchestration with producer-consumer, cancellation, and safety
# ------------------------------------------------------------------------------
@dataclass
class ParserExecutionState:
    """State container for VLM extraction."""
    results: Dict[int, Optional[Dict[str, Any]]]
    running_pages: Set[int]
    completed_count: int
    failed_count: int
    page_timeouts: int
    global_timeout: bool
    started_at: float
    last_heartbeat: float
    results_lock: threading.Lock
    running_pages_lock: threading.Lock
    total_pages: int
    parser_choice: str
    memory_peak_mb: float = 0.0

def execute_vlm_document_graph_extraction(
    images: Sequence[Any],
    pipeline_id: Optional[str] = None,
    max_workers: int = 2,
    trace_fn: Optional[Callable[[str], None]] = None,
    progress_json: Optional[Dict[str, Any]] = None,
    on_page_completed: Optional[Callable[[int, Dict[str, Any]], None]] = None,
    cancellation_check: Optional[Callable[[], bool]] = None,
    timeout_check: Optional[Callable[[], bool]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Perform VLM document graph extraction with per‑page and global timeouts,
    cooperative cancellation, bounded concurrency, and heartbeat.
    """
    image_list = list(images or [])
    if not image_list:
        raise ValueError("No images provided for VLM document graph extraction")

    max_workers = max(1, int(max_workers or 2))
    if max_workers > getattr(config, "MAX_VLM_WORKERS", 4):
        max_workers = getattr(config, "MAX_VLM_WORKERS", 4)

    document_id = str(pipeline_id or f"document_{int(time.time() * 1000)}")
    started_at = time.perf_counter()
    last_heartbeat = started_at
    heartbeat_interval = HEARTBEAT_INTERVAL_SECONDS

    # Capture filename early to avoid race
    first_image = image_list[0] if image_list else None
    original_filename = os.path.basename(getattr(first_image, 'filename', str(document_id))) if first_image else str(document_id)
    if original_filename.startswith("document_"):
        original_filename = "document.pdf" if _is_pdf_file(str(document_id)) else "document_image"

    # Determine parser choice (gemini or ocr) from progress_json or availability
    parser_choice = "gemini" if _get_gemini_api_key() else "ocr"
    if progress_json and progress_json.get("parser"):
        parser_choice = progress_json.get("parser")

    _trace(trace_fn, f"[VLM] Selected parser: {parser_choice}")

    # Load previously completed pages from progress checkpoint
    completed_pages = set(progress_json.get("completed_pages", []) if progress_json else [])
    completed_pages_data = progress_json.get("completed_pages_data", {}) if progress_json else {}

    # Thread-safe structures
    results_lock = threading.Lock()
    results: Dict[int, Optional[Dict[str, Any]]] = {}
    for pnum_str, page_graph in completed_pages_data.items():
        try:
            pnum = int(pnum_str)
            results[pnum - 1] = page_graph
        except Exception:
            pass

    running_pages_lock = threading.Lock()
    running_pages: Set[int] = set()

    # Create state object
    state = ParserExecutionState(
        results=results,
        running_pages=running_pages,
        completed_count=0,
        failed_count=0,
        page_timeouts=0,
        global_timeout=False,
        started_at=started_at,
        last_heartbeat=last_heartbeat,
        results_lock=results_lock,
        running_pages_lock=running_pages_lock,
        total_pages=len(image_list),
        parser_choice=parser_choice,
        memory_peak_mb=_rss_mb(),
    )

    # Helper to clean up image references
    def _cleanup_image(page_index: int):
        if page_index < len(image_list):
            image_list[page_index] = None
        if isinstance(images, list) and page_index < len(images):
            try:
                images[page_index] = None
            except Exception:
                pass

    # Worker function per page
    def _process_page(page_index: int, image: Any, page_start_time: float) -> Optional[Dict[str, Any]]:
        page_number = page_index + 1
        # Check cancellation and timeout before processing
        if cancellation_check and cancellation_check():
            raise ParserCancelledError(f"Cancelled before processing page {page_number}")
        if timeout_check and timeout_check():
            raise ParserTimeoutError(f"Global timeout exceeded before processing page {page_number}")

        if parser_choice == "gemini":
            # Directly call Gemini parser; it returns validated dict
            try:
                graph_data = _call_gemini_page_parser(
                    image=image,
                    page_number=page_number,
                    pipeline_id=pipeline_id,
                    timeout_seconds=PAGE_PARSE_TIMEOUT_SECONDS,
                    retries=MAX_PAGE_RETRIES,
                    trace_fn=trace_fn,
                    cancellation_check=cancellation_check,
                    timeout_check=timeout_check,
                    page_start_time=page_start_time,
                )
                return graph_data
            except (GeminiRateLimitError, ParserCancelledError, ParserTimeoutError, GeminiPermanentError) as e:
                # Re-raise these to stop or propagate
                raise
            # Do NOT catch all exceptions here; let unexpected ones propagate.
        else:
            try:
                fallback_page = _ocr_fallback_page(image, page_number)
                if fallback_page is not None:
                    fallback_page["fallback_reason"] = "Gemini unavailable upfront, utilizing OCR fallback"
                    return fallback_page
                return None
            except Exception as e:
                # OCR may raise, but we don't want it to stop the whole extraction
                _trace(trace_fn, f"[VLM] OCR fallback failed on page {page_number}: {e}")
                return None

    def _worker_task(page_index: int, image: Any, page_start_time: float):
        page_number = page_index + 1
        # Check if already completed or running (double-check under lock)
        with state.results_lock:
            if page_index in state.results:
                _cleanup_image(page_index)
                return state.results[page_index]
        with state.running_pages_lock:
            if page_index in state.running_pages:
                return None
            state.running_pages.add(page_index)

        try:
            res = _process_page(page_index, image, page_start_time)
            with state.results_lock:
                state.results[page_index] = res
                if res is not None:
                    state.completed_count += 1
                else:
                    state.failed_count += 1

            # Checkpoint
            if res is not None and on_page_completed:
                try:
                    on_page_completed(page_number, res)
                    _trace(trace_fn, f"[VLM] Page {page_number} checkpointed via callback")
                except Exception as cb_err:
                    _trace(trace_fn, f"[VLM] Warning: page completion callback failed: {cb_err}")

            return res
        except (ParserCancelledError, ParserTimeoutError, GeminiRateLimitError) as e:
            # Propagate these to stop the extraction
            with state.results_lock:
                state.results[page_index] = None
                state.failed_count += 1
            raise
        except Exception as e:
            # Catch-all for truly unexpected errors (should not happen)
            with state.results_lock:
                state.results[page_index] = None
                state.failed_count += 1
            _trace(trace_fn, f"[VLM] Unhandled error on page {page_number}: {e}")
            return None
        finally:
            with state.running_pages_lock:
                state.running_pages.discard(page_index)
            _cleanup_image(page_index)
            if page_index % MEMORY_GC_INTERVAL == 0:
                gc.collect()
                # Update memory peak
                current_mem = _rss_mb()
                if current_mem > state.memory_peak_mb:
                    state.memory_peak_mb = current_mem

    # Determine which pages to process
    to_process = [idx for idx in range(len(image_list)) if idx not in state.results]
    total_pages = len(image_list)

    # Producer-consumer with bounded concurrency
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
    pending_futures: Set[concurrent.futures.Future] = set()
    future_to_idx: Dict[concurrent.futures.Future, int] = {}
    idx_iter = iter(to_process)

    try:
        # Initial fill
        while len(pending_futures) < max_workers:
            try:
                idx = next(idx_iter)
            except StopIteration:
                break
            # Check if page already completed (should not happen)
            with state.results_lock:
                if idx in state.results:
                    continue
            page_start_time = time.time()
            future = executor.submit(_worker_task, idx, image_list[idx], page_start_time)
            pending_futures.add(future)
            future_to_idx[future] = idx

        # Main loop
        while pending_futures:
            # Check global timeout and cancellation
            now = time.perf_counter()
            if timeout_check and timeout_check():
                _trace(trace_fn, f"[VLM] Global timeout exceeded after {now - state.started_at:.1f}s")
                state.global_timeout = True
                for f in pending_futures:
                    f.cancel()
                break
            if cancellation_check and cancellation_check():
                _trace(trace_fn, "[VLM] Cancellation requested")
                for f in pending_futures:
                    f.cancel()
                raise ParserCancelledError("Cancellation requested during VLM extraction")

            # Heartbeat
            if now - state.last_heartbeat >= heartbeat_interval:
                state.last_heartbeat = now
                with state.results_lock:
                    completed = state.completed_count
                    failed = state.failed_count
                with state.running_pages_lock:
                    running_info = [f"{idx+1} (running)" for idx in state.running_pages]
                # Compute ETA based on recent completion rate
                elapsed = now - state.started_at
                eta = "unknown"
                if completed > 0 and elapsed > 0:
                    rate = completed / elapsed
                    remaining = total_pages - completed - failed
                    if rate > 0:
                        eta_sec = remaining / rate
                        if eta_sec < 60:
                            eta = f"{eta_sec:.0f}s"
                        elif eta_sec < 3600:
                            eta = f"{eta_sec/60:.1f}m"
                        else:
                            eta = f"{eta_sec/3600:.1f}h"
                _trace(trace_fn, f"[VLM] Heartbeat: completed {completed}/{total_pages}, "
                        f"failed {failed}, running {len(running_info)}, pending {len(pending_futures)}, "
                        f"elapsed {elapsed:.1f}s, memory {state.memory_peak_mb:.1f}MB, "
                        f"workers={max_workers}, retries={MAX_PAGE_RETRIES}, ETA={eta}")

            # Wait for any future to complete with a short timeout
            done, _ = concurrent.futures.wait(pending_futures, timeout=1.0, return_when=concurrent.futures.FIRST_COMPLETED)
            for future in done:
                idx = future_to_idx.pop(future, None)
                if idx is not None:
                    pending_futures.remove(future)
                    # If future had an exception, we may need to handle it
                    try:
                        future.result()  # Raises if exception occurred
                    except Exception as e:
                        if isinstance(e, (ParserCancelledError, ParserTimeoutError, GeminiRateLimitError)):
                            # Critical error, stop extraction
                            for f in pending_futures:
                                f.cancel()
                            raise
                        # Otherwise, page already marked failed (swallowed in worker_task)
                        pass
                    # Submit next page if any
                    try:
                        next_idx = next(idx_iter)
                    except StopIteration:
                        continue
                    with state.results_lock:
                        if next_idx in state.results:
                            continue
                    if cancellation_check and cancellation_check():
                        raise ParserCancelledError("Cancellation requested before submitting next page")
                    if timeout_check and timeout_check():
                        state.global_timeout = True
                        break
                    page_start_time = time.time()
                    future_new = executor.submit(_worker_task, next_idx, image_list[next_idx], page_start_time)
                    pending_futures.add(future_new)
                    future_to_idx[future_new] = next_idx

            if state.global_timeout:
                break

    finally:
        # Shutdown executor: wait for all running tasks to finish (they have bounded timeouts)
        executor.shutdown(wait=True)

    # After loop, any pages not processed due to timeout are marked as failed
    if state.global_timeout:
        with state.results_lock:
            for idx in to_process:
                if idx not in state.results:
                    state.results[idx] = None

    # Build final graph (recompute statistics from graph, not trusting incremental counters)
    pages: List[Dict[str, Any]] = []
    total_failed = 0
    total_vlm_success = 0
    total_ocr_success = 0
    total_nodes = 0
    total_edges = 0
    document_edges: List[Dict[str, Any]] = []
    previous_last_node_id: Optional[str] = None

    # Track seen edges to avoid duplicates
    seen_edges: Set[Tuple[str, str]] = set()

    for page_index in range(len(image_list)):
        page_graph = state.results.get(page_index)
        if page_graph is None:
            total_failed += 1
            continue

        pages.append(page_graph)
        page_nodes = page_graph.get("nodes", []) if isinstance(page_graph, dict) else []
        page_edges = page_graph.get("edges", []) if isinstance(page_graph, dict) else []
        total_nodes += len(page_nodes)
        total_edges += len(page_edges)
        if page_graph.get("source") == "gemini":
            total_vlm_success += 1
        elif page_graph.get("source") == "ocr":
            total_ocr_success += 1

        if page_nodes:
            first_node_id = page_nodes[0].get("chunk_id")
            if previous_last_node_id and first_node_id:
                edge_key = (previous_last_node_id, first_node_id)
                if edge_key not in seen_edges:
                    document_edges.append(
                        {
                            "from": previous_last_node_id,
                            "to": first_node_id,
                            "relation": "PAGE_NEXT",
                        }
                    )
                    seen_edges.add(edge_key)
            previous_last_node_id = page_nodes[-1].get("chunk_id") or previous_last_node_id

    failure_ratio = total_failed / max(len(image_list), 1)
    if failure_ratio > FAILURE_RATIO_THRESHOLD:
        _trace(trace_fn, f"[VLM] Warning: high failure ratio {failure_ratio:.0%} for {total_failed}/{len(image_list)} pages")

    # Determine file type based on original filename if available, else fallback
    file_type = "unknown"
    if original_filename:
        ext = os.path.splitext(original_filename)[1].lower()
        if ext == ".pdf":
            file_type = "pdf"
        elif ext in SUPPORTED_IMAGE_EXTENSIONS:
            file_type = "image"
    else:
        if pipeline_id and isinstance(pipeline_id, str):
            if pipeline_id.endswith(".pdf"):
                file_type = "pdf"
            elif any(pipeline_id.endswith(ext) for ext in SUPPORTED_IMAGE_EXTENSIONS):
                file_type = "image"

    # Recompute node and edge counts from graph to avoid incremental errors
    final_node_count = sum(len(pg.get("nodes", [])) for pg in pages)
    final_edge_count = sum(len(pg.get("edges", [])) for pg in pages) + len(document_edges)

    graph = {
        "document_id": document_id,
        "parser": "gemini_vlm" if parser_choice == "gemini" else "tesseract_ocr",
        "schema_version": "1.0",
        "document_type": "MULTIMODAL",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "page_count": len(image_list),
        "pages": pages,
        "edges": document_edges,
        "statistics": {
            "page_count": len(image_list),
            "node_count": final_node_count,
            "edge_count": final_edge_count,
            "vlm_success_pages": total_vlm_success,
            "ocr_fallback_pages": total_ocr_success,
            "failed_pages": total_failed,
            "timeout_pages": state.page_timeouts,
            "global_timeout_triggered": state.global_timeout,
            "duration_seconds": round(time.perf_counter() - state.started_at, 3),
        },
        "document_metadata": {
            "filename": original_filename,
            "file_type": file_type,
            "page_count": len(image_list),
            "parser": "gemini_vlm" if parser_choice == "gemini" else "tesseract_ocr",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "pipeline_id": pipeline_id,
        },
    }

    # Debug output
    logger.error(
        "\n========== GRAPH DEBUG =========="
        f"\nVLM pages={total_vlm_success}"
        f"\nOCR pages={total_ocr_success}"
        f"\nFailed pages={total_failed}"
        f"\nTotal nodes={final_node_count}"
        f"\nFirst page nodes={len(pages[0]['nodes']) if pages else 0}"
        "\n================================="
    )

    return graph


# Helper to get RSS memory
def _rss_mb() -> float:
    try:
        return psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
    except Exception:
        return 0.0


# ------------------------------------------------------------------------------
# Legacy wrapper and public APIs (unchanged, but we pass through new params)
# ------------------------------------------------------------------------------
def run_enhancement_pipeline(
    filepath: str,
    report: Optional[PreprocessingReport] = None,
    pipeline_id: Optional[str] = None,
    output_dir: Optional[str] = None,
    page_count: Optional[int] = None,
    trace_fn: Optional[Callable[[str], None]] = None,
) -> Optional[str]:
    started_at = time.perf_counter()
    try:
        preprocessor = DocumentPreprocessor(filepath)
        base_output_dir = output_dir or os.path.join(_CURRENT_DIR, "storage", "temp")
        os.makedirs(base_output_dir, exist_ok=True)
        enhancement_dir = os.path.join(
            base_output_dir,
            f"{pipeline_id or os.path.splitext(preprocessor.filename)[0]}_enhanced_pages",
        )
        os.makedirs(enhancement_dir, exist_ok=True)

        max_pages = page_count or getattr(config, "PREPROCESS_MAX_ENHANCE_PAGES", 25)
        rendered_images = preprocessor.render_document(max_pages=max_pages, dpi=getattr(config, "PREPROCESS_TARGET_DPI", 300), trace_fn=trace_fn)

        saved_paths: List[str] = []
        for page_index, image in enumerate(rendered_images, start=1):
            pil_image = _ensure_pil_image(image)
            processed = _enhance_numpy_image(np.array(pil_image.convert("RGB")))
            if PIL_AVAILABLE:
                output_image = Image.fromarray(cv2.cvtColor(processed, cv2.COLOR_BGR2RGB))
            else:
                output_image = pil_image
            page_path = os.path.join(enhancement_dir, f"page_{page_index:04d}.png")
            output_image.save(page_path, format="PNG")
            saved_paths.append(page_path)

        if report is not None:
            report.enhancement_flags["enhanced_page_count"] = len(saved_paths)
            report.enhancement_flags["enhancement_dir"] = enhancement_dir
            report.timings["enhancement_secs"] = round(time.perf_counter() - started_at, 3)

        _trace(trace_fn, f"[PREPROCESS] Enhancement pipeline saved {len(saved_paths)} page(s) to {enhancement_dir}")
        return enhancement_dir if saved_paths else None
    except Exception as exc:
        _trace(trace_fn, f"[PREPROCESS] Enhancement pipeline failed: {exc}")
        if report is not None:
            report.warnings.append(f"Enhancement pipeline failed: {exc}")
            report.timings["enhancement_secs"] = round(time.perf_counter() - started_at, 3)
        return None


def execute_vlm_extraction_step(
    images: Sequence[Any],
    pipeline_id: Optional[str] = None,
    max_workers: int = 2,
    trace_fn: Optional[Callable[[str], None]] = None,
    **kwargs: Any,
) -> Optional[Dict[str, Any]]:
    # Pass through new parameters if provided
    cancellation_check = kwargs.get("cancellation_check")
    timeout_check = kwargs.get("timeout_check")
    return execute_vlm_document_graph_extraction(
        images=images,
        pipeline_id=pipeline_id,
        max_workers=max_workers,
        trace_fn=trace_fn,
        cancellation_check=cancellation_check,
        timeout_check=timeout_check,
        **{k: v for k, v in kwargs.items() if k not in ("cancellation_check", "timeout_check")}
    )


def parse_document_vlm(
    file_path: Optional[str] = None,
    images: Optional[Sequence[Any]] = None,
    pipeline_id: Optional[str] = None,
    max_workers: int = 2,
    trace_fn: Optional[Callable[[str], None]] = None,
    **kwargs: Any,
) -> Any:
    if file_path is None and images is None:
        raise ValueError("Either file_path or images must be provided")

    if file_path is not None and _is_text_file(file_path):
        with open(file_path, "r", encoding="utf-8", errors="ignore") as handle:
            return handle.read()

    if images is None:
        preprocessor = DocumentPreprocessor(str(file_path))
        images = preprocessor.render_document(trace_fn=trace_fn)

    cancellation_check = kwargs.get("cancellation_check")
    timeout_check = kwargs.get("timeout_check")
    return execute_vlm_document_graph_extraction(
        images=images,
        pipeline_id=pipeline_id,
        max_workers=max_workers,
        trace_fn=trace_fn,
        cancellation_check=cancellation_check,
        timeout_check=timeout_check,
        **{k: v for k, v in kwargs.items() if k not in ("cancellation_check", "timeout_check")}
    )


def preprocess_document(
    file_path: str,
    trace_fn: Optional[Callable[[str], None]] = None,
    **kwargs: Any,
) -> PreprocessingReport:
    return evaluate_document(file_path=file_path, trace_fn=trace_fn, **kwargs)


def evaluate_document(
    file_path: str,
    trace_fn: Optional[Callable[[str], None]] = None,
    *args: Any,
    **kwargs: Any,
) -> PreprocessingReport:
    return DocumentPreprocessor(file_path).generate_routing_report(trace_fn=trace_fn)


def structural_guard(file_path: str, *args: Any, **kwargs: Any) -> None:
    # Perform fast/light structural check (fast pass count & decryption check)
    # to guarantee we return under 5 seconds during synchronous upload guard.
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    if file_path.lower().endswith(".pdf"):
        import pypdf
        try:
            reader = pypdf.PdfReader(file_path)
            if reader.is_encrypted:
                # Decrypt attempt
                try:
                    if reader.decrypt("") == 0:
                        raise ValueError("PDF is encrypted with password")
                except:
                    raise ValueError("PDF is encrypted")
            if len(reader.pages) <= 0:
                raise ValueError("PDF contains no pages")
        except Exception as e:
            raise ValueError(f"Invalid PDF structure: {e}")
    return None


__all__ = [
    "CV2_AVAILABLE",
    "PDF2IMAGE_AVAILABLE",
    "PIL_AVAILABLE",
    "PYTESSERACT_AVAILABLE",
    "GEMINI_MIN_INTERVAL_SECONDS",
    "GEMINI_MODEL_NAME",
    "DOCUMENT_GRAPH_PROMPT",
    "PreprocessingReport",
    "DocumentPreprocessor",
    "analyze_image_spatial_quality",
    "_score_text_coherence",
    "_gemini_throttle",
    "_check_memory_before_render",
    "_pil_to_base64",
    "_call_gemini_page_parser",
    "execute_vlm_document_graph_extraction",
    "execute_vlm_extraction_step",
    "parse_document_vlm",
    "run_enhancement_pipeline",
    "evaluate_document",
    "preprocess_document",
    "structural_guard",
    "logger",
]