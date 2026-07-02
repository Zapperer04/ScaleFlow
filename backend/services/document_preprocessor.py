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
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

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
      "type": "heading|subheading|paragraph|table|list|equation|figure|caption|footer|header|reference|code|quote|form_field",
      "text": "...",
      "reading_order": 1,
      "section": "...",
      "bbox": {
        "x1": 0,
        "y1": 0,
        "x2": 0,
        "y2": 0
      }
    }
  ]
}

Rules:
- Return normalized bounding boxes in the 0 to 1 range when possible.
- Use only the allowed node types.
- Preserve the visual reading order.
- Keep text verbatim where possible.
- If the page is blank, return an empty nodes array.
- The response must be a single JSON object.
"""


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
    estimated_mb = pages_to_render * 30.0 * (target_dpi / 72.0) ** 2
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
    allowed = {
        "heading",
        "subheading",
        "paragraph",
        "table",
        "list",
        "equation",
        "figure",
        "caption",
        "footer",
        "header",
        "reference",
        "code",
        "quote",
        "form_field",
    }
    value = str(node_type or "paragraph").strip().lower()
    return value if value in allowed else "paragraph"


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


def _generate_spatial_edges(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Build spatial relationships between nodes using bounding box overlap and relative positions.
    Returns a list of edges with relations: ABOVE, BELOW, LEFT_OF, RIGHT_OF, INSIDE.
    """
    edges = []
    if len(nodes) < 2:
        return edges

    # Pre-extract boxes
    node_data = []
    for node in nodes:
        bbox = node.get("bbox", {})
        x1 = _safe_float(bbox.get("x1", 0))
        y1 = _safe_float(bbox.get("y1", 0))
        x2 = _safe_float(bbox.get("x2", 1))
        y2 = _safe_float(bbox.get("y2", 1))
        node_data.append((node["chunk_id"], x1, y1, x2, y2))

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

            # Vertical relationship
            if y2_i <= y1_j:
                edges.append({"from": id_i, "to": id_j, "relation": "ABOVE"})
            elif y2_j <= y1_i:
                edges.append({"from": id_j, "to": id_i, "relation": "ABOVE"})
            # Horizontal relationship
            elif x2_i <= x1_j:
                edges.append({"from": id_i, "to": id_j, "relation": "LEFT_OF"})
            elif x2_j <= x1_i:
                edges.append({"from": id_j, "to": id_i, "relation": "LEFT_OF"})
            # Overlap but not inside: could still be considered ABOVE/BELOW if vertical offset large
            # For simplicity we skip ambiguous cases.

    return edges


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
        # Fix: don't open file inside context manager, use file path directly
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
                    # Fix: route encrypted PDF to VLM instead of hard reject
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


def _call_gemini_page_parser(
    image: Any,
    page_number: Optional[int] = None,
    pipeline_id: Optional[str] = None,
    timeout_seconds: int = 300,
    retries: int = 4,
    trace_fn: Optional[Callable[[str], None]] = None,
) -> str:
    api_key = _get_gemini_api_key()
    if not api_key:
        raise RuntimeError("Gemini API key is not configured")

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
            "maxOutputTokens": 16384,  # increased from 8192
            "responseMimeType": "application/json",
        },
    }
    url = GEMINI_API_URL_TEMPLATE.format(model=GEMINI_MODEL_NAME, api_key=api_key)
    headers = {"Content-Type": "application/json"}

    last_exception: Optional[BaseException] = None
    for attempt in range(max(1, retries)):
        try:
            _gemini_throttle()
            response = requests.post(url, headers=headers, json=body, timeout=timeout_seconds)
            if response.status_code >= 500 or response.status_code == 429:
                raise RuntimeError(f"Gemini returned HTTP {response.status_code}: {response.text[:500]}")
            response.raise_for_status()
            response_json = response.json()
            raw_text = _extract_gemini_text(response_json)
            cleaned = _clean_json_text(raw_text)
            if not cleaned:
                raise ValueError("Gemini response did not contain JSON text")
            json.loads(cleaned)
            return cleaned
        except Exception as exc:
            last_exception = exc
            if attempt >= retries - 1:
                break
            backoff_seconds = min(20.0, (2.0 ** attempt) + (0.25 * attempt))
            _trace(trace_fn, f"[VLM] Gemini page parser retry {attempt + 1}/{retries} after error: {exc}")
            time.sleep(backoff_seconds)

    raise RuntimeError(f"Gemini page parser failed after {retries} attempts: {last_exception}")


def _ocr_fallback_page(image: Any, page_number: int) -> Optional[Dict[str, Any]]:
    if not PYTESSERACT_AVAILABLE or pytesseract is None:
        return None

    try:
        pil_image = _ensure_pil_image(image)
        width, height = pil_image.size

        # Use image_to_data to preserve layout (word-level bboxes)
        data = pytesseract.image_to_data(pil_image, output_type=Output.DICT, config="--psm 6")
        nodes = []
        n_boxes = len(data['level'])
        for i in range(n_boxes):
            # level 5 is word
            if data['level'][i] == 5:
                text = data['text'][i].strip()
                if not text:
                    continue
                x = data['left'][i]
                y = data['top'][i]
                w = data['width'][i]
                h = data['height'][i]
                conf = int(data['conf'][i]) if data['conf'][i] != '-1' else 0
                # Skip very low confidence words
                if conf < 20:
                    continue
                # Normalize bbox
                bbox = {
                    "x1": x / width,
                    "y1": y / height,
                    "x2": (x + w) / width,
                    "y2": (y + h) / height,
                }
                nodes.append({
                    "chunk_id": f"p{page_number}_ocr_word_{i}",
                    "type": "paragraph",
                    "text": text,
                    "section": "ocr_fallback",
                    "reading_order": i,  # approximate
                    "bbox": bbox,
                })

        if not nodes:
            # fallback: full page single node
            full_text = pytesseract.image_to_string(pil_image, config="--psm 6").strip()
            if not full_text:
                return None
            node = {
                "chunk_id": f"p{page_number}_n1",
                "type": "paragraph",
                "text": full_text,
                "section": "ocr_fallback",
                "reading_order": 1,
                "bbox": {"x1": 0.0, "y1": 0.0, "x2": 1.0, "y2": 1.0},
            }
            nodes = [node]

        # Sort by reading_order (by index) for sequential edges later
        nodes.sort(key=lambda n: n["reading_order"])
        # Build spatial edges for this page
        spatial_edges = _generate_spatial_edges(nodes)
        # Sequential edges between consecutive nodes
        seq_edges = []
        for idx in range(len(nodes) - 1):
            seq_edges.append({
                "from": nodes[idx]["chunk_id"],
                "to": nodes[idx + 1]["chunk_id"],
                "relation": "NEXT",
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
        }
        return page_graph
    except Exception:
        return None


def _normalize_page_graph(
    page_number: int,
    raw_json_text: str,
    image: Any,
) -> Dict[str, Any]:
    payload = json.loads(raw_json_text)
    if not isinstance(payload, dict):
        raise ValueError("Gemini response was not a JSON object")

    nodes = payload.get("nodes")
    if nodes is None:
        raise ValueError("Gemini response did not include nodes")
    if not isinstance(nodes, list):
        raise ValueError("nodes must be a list")

    pil_image = _ensure_pil_image(image)
    width, height = pil_image.size

    normalized_nodes: List[Dict[str, Any]] = []
    ordered_nodes: List[Tuple[int, Dict[str, Any]]] = []

    for index, node in enumerate(nodes, start=1):
        if not isinstance(node, dict):
            continue
        raw_reading_order = node.get("reading_order", index)
        try:
            reading_order = int(raw_reading_order)
        except Exception:
            reading_order = index
        ordered_nodes.append((reading_order, node))

    ordered_nodes.sort(key=lambda item: (item[0],))

    for sequence_index, (_, node) in enumerate(ordered_nodes, start=1):
        normalized_nodes.append(
            {
                "chunk_id": f"p{page_number}_n{sequence_index}",
                "type": _normalize_node_type(node.get("type")),
                "text": str(node.get("text", "") or "").strip(),
                "section": str(node.get("section", "") or "").strip(),
                "reading_order": sequence_index,
                "bbox": _normalize_bbox(node.get("bbox"), width, height),
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
    spatial_edges = _generate_spatial_edges(normalized_nodes)
    edges.extend(spatial_edges)

    return {
        "page_number": page_number,
        "source": "gemini",
        "width": width,
        "height": height,
        "nodes": normalized_nodes,
        "edges": edges,
        "status": "success",
    }


def execute_vlm_document_graph_extraction(
    images: Sequence[Any],
    pipeline_id: Optional[str] = None,
    max_workers: int = 2,
    trace_fn: Optional[Callable[[str], None]] = None,
) -> Optional[Dict[str, Any]]:
    image_list = list(images or [])
    if not image_list:
        raise ValueError("No images provided for VLM document graph extraction")

    max_workers = max(1, int(max_workers or 2))
    document_id = str(pipeline_id or f"document_{int(time.time() * 1000)}")
    started_at = time.perf_counter()

    def _process_page(page_index: int, image: Any) -> Optional[Dict[str, Any]]:
        page_number = page_index + 1
        _trace(trace_fn, f"[VLM] Processing page {page_number}/{len(image_list)}")
        try:
            raw_text = _call_gemini_page_parser(
                image=image,
                page_number=page_number,
                pipeline_id=pipeline_id,
                trace_fn=trace_fn,
            )
            return _normalize_page_graph(page_number=page_number, raw_json_text=raw_text, image=image)
        except Exception as exc:
            _trace(trace_fn, f"[VLM] Gemini failed on page {page_number}: {exc}")
            fallback_page = _ocr_fallback_page(image, page_number)
            if fallback_page is not None:
                _trace(trace_fn, f"[VLM] OCR fallback succeeded on page {page_number}")
                return fallback_page
            _trace(trace_fn, f"[VLM] OCR fallback failed on page {page_number}")
            return None

    results: Dict[int, Optional[Dict[str, Any]]] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(_process_page, page_index, image): page_index
            for page_index, image in enumerate(image_list)
        }
        for future in concurrent.futures.as_completed(future_map):
            page_index = future_map[future]
            try:
                results[page_index] = future.result()
            except Exception as exc:
                _trace(trace_fn, f"[VLM] Unexpected page worker failure on page {page_index + 1}: {exc}")
                results[page_index] = None

    pages: List[Dict[str, Any]] = []
    total_failed = 0
    total_vlm_success = 0
    total_ocr_success = 0
    total_nodes = 0
    total_edges = 0
    document_edges: List[Dict[str, Any]] = []
    previous_last_node_id: Optional[str] = None

    for page_index in range(len(image_list)):
        page_graph = results.get(page_index)
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
                document_edges.append(
                    {
                        "from": previous_last_node_id,
                        "to": first_node_id,
                        "relation": "PAGE_NEXT",
                    }
                )
            previous_last_node_id = page_nodes[-1].get("chunk_id") or previous_last_node_id

    failure_ratio = total_failed / max(len(image_list), 1)
    # More lenient threshold for VLM pipelines
    if failure_ratio > 0.50:
        raise RuntimeError(
            f"Document graph extraction failed for {total_failed}/{len(image_list)} pages ({failure_ratio:.0%})"
        )

    graph = {
        "document_id": document_id,
        "parser": "gemini_vlm",
        "schema_version": "1.0",
        "document_type": "MULTIMODAL",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "page_count": len(image_list),
        "pages": pages,
        "edges": document_edges,
        "statistics": {
            "page_count": len(image_list),
            "node_count": total_nodes,
            "edge_count": total_edges + len(document_edges),
            "vlm_success_pages": total_vlm_success,
            "ocr_fallback_pages": total_ocr_success,
            "failed_pages": total_failed,
            "duration_seconds": round(time.perf_counter() - started_at, 3),
        },
        "document_metadata": {
            "filename": os.path.basename(images[0] if hasattr(images[0], 'filename') else document_id),
            "file_type": "image" if not _is_pdf_file(str(document_id)) else "pdf",
            "page_count": len(image_list),
            "parser": "gemini_vlm",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "pipeline_id": pipeline_id,
        },
    }
    return graph


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
    return execute_vlm_document_graph_extraction(
        images=images,
        pipeline_id=pipeline_id,
        max_workers=max_workers,
        trace_fn=trace_fn,
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

    return execute_vlm_document_graph_extraction(
        images=images,
        pipeline_id=pipeline_id,
        max_workers=max_workers,
        trace_fn=trace_fn,
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


def structural_guard(*args: Any, **kwargs: Any) -> None:
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