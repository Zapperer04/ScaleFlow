"""
pdf_parser.py — Hardened PDF extraction service for ScaleFlow.

Fallback chain per page:
  PRIMARY   → pypdf       (fast, pure-Python, reliable for text PDFs)
  FALLBACK  → pdfplumber  (better layout recovery, two-column, mixed formatting)
  FINAL     → pytesseract (OCR, activated ONLY for scanned/image-only pages)

Resource guards:
  - MAX_PAGES:      600 pages hard cap (env PDF_MAX_PAGES)
  - MEMORY_LIMIT:   1500 MB RSS — checked every 50 pages
  - PARSE_TIMEOUT:  1800 seconds (30 min) — existing ceiling kept
  - LOW_TEXT_CHARS: < 20 chars on a page = candidate for fallback/OCR

All parser decisions and progress are returned as structured ParseResult
and also emitted via a callback so the worker can forward them to the
event trace stream.
"""

from __future__ import annotations

import os
import time
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Quality Evaluation Helper
# ──────────────────────────────────────────────────────────────────────────────
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from services.quality_gate_service import compute_quality_score

# ──────────────────────────────────────────────────────────────────────────────
# Load vocabulary once at import time to prevent spacing regressions (Phase 2)
# ──────────────────────────────────────────────────────────────────────────────
_VOCAB = set()
try:
    _services_dir = os.path.dirname(os.path.abspath(__file__))
    _backend_dir = os.path.dirname(_services_dir)
    _hf_cache_dir = os.path.join(_backend_dir, "hf_cache")
    if os.path.exists(_hf_cache_dir):
        from pathlib import Path
        for p in Path(_hf_cache_dir).glob("**/vocab.txt"):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        w = line.strip().lower()
                        if w and not w.startswith("##"):
                            _VOCAB.add(w)
            except Exception:
                pass
except Exception:
    pass

_COMMON_WORDS = {
    "ray", "library", "value", "tree", "cell", "combinator", "notes", "protocol",
    "systems", "model", "mode", "base", "data", "point", "type", "file", "user",
    "code", "test", "page", "line", "word", "char", "name", "link", "view", "task",
    "tool", "run", "set", "get", "score", "rate", "flow", "scale", "level", "step"
}
_VOCAB.update(_COMMON_WORDS)


# ──────────────────────────────────────────────────────────────────────────────
# Configuration (overridable via environment)
# ──────────────────────────────────────────────────────────────────────────────
MAX_PAGES        = config.PDF_MAX_PAGES
MEMORY_LIMIT_MB  = config.PDF_MEMORY_LIMIT_MB
PARSE_TIMEOUT_S  = config.PDF_PARSE_TIMEOUT_S
LOW_TEXT_THRESH  = config.PDF_LOW_TEXT_CHARS
MEMORY_CHECK_EVERY = 50   # check RSS every N pages


# ──────────────────────────────────────────────────────────────────────────────
# Result dataclass
# ──────────────────────────────────────────────────────────────────────────────
@dataclass
class ParseResult:
    text: str = ""
    stats: dict = field(default_factory=dict)
    pages: list[dict] = field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────────────
# Optional library probes — import failures are handled gracefully
# ──────────────────────────────────────────────────────────────────────────────
def _probe_pdfplumber():
    try:
        import pdfplumber  # noqa: F401
        return True
    except ImportError:
        return False

def _probe_ocr():
    """Returns True only if both pytesseract AND poppler (pdf2image) are available."""
    try:
        import pytesseract  # noqa: F401
        from pdf2image import convert_from_path  # noqa: F401
        # Quick sanity check — Tesseract binary must exist
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False

PDFPLUMBER_AVAILABLE = _probe_pdfplumber()
OCR_AVAILABLE        = _probe_ocr()


# ──────────────────────────────────────────────────────────────────────────────
# Page heuristics and features (Phase 2 Directive)
# ──────────────────────────────────────────────────────────────────────────────
def _render_page_thumbnail(filepath: str, page_index: int) -> Optional[Any]:
    from pdf2image import convert_from_path
    poppler_path = getattr(config, "PREPROCESS_POPPLER_PATH", None) or os.getenv("PREPROCESS_POPPLER_PATH") or None
    try:
        images = convert_from_path(
            filepath,
            first_page=page_index + 1,
            last_page=page_index + 1,
            dpi=72,
            poppler_path=poppler_path
        )
        return images[0] if images else None
    except Exception:
        return None


def _detect_table(img) -> bool:
    import cv2
    import numpy as np
    gray = np.array(img.convert("L"))
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(
        edges, 1, np.pi / 180,
        threshold=50,
        minLineLength=gray.shape[1] // 8,
        maxLineGap=10,
    )
    if lines is None:
        return False
    h_lines = v_lines = 0
    for line in lines:
        x1, y1, x2, y2 = line[0]
        slope = abs(float(y2 - y1)) / (abs(float(x2 - x1)) + 1e-6)
        if slope < 0.2:    # near-horizontal
            h_lines += 1
        elif slope > 5.0:  # near-vertical
            v_lines += 1
    return h_lines >= 3 and v_lines >= 2


def _detect_signature(img) -> bool:
    import cv2
    import numpy as np
    gray = np.array(img.convert("L"))
    h, w = gray.shape
    roi = gray[int(h * 0.70):, :]
    binary = cv2.adaptiveThreshold(
        roi, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        11, 2,
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


def _compute_handwriting_score(img) -> float:
    import cv2
    import numpy as np
    try:
        gray = np.array(img.convert("L"))
        binary = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            11, 2,
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


def _determine_page_routing_and_type(reader, page_index: int, filepath: str, parse_method_hint: str, plumber_reader=None) -> tuple[str, str, float]:
    """
    Determine detected page type, chosen parser, and confidence without rendering unless scanned.
    """
    # 1. Try to check digital text content
    text = ""
    try:
        page = reader.pages[page_index]
        text = page.extract_text() or ""
    except Exception:
        pass
    
    chars = len(text.strip())
    
    # Check if page is digital
    is_digital = False
    if chars > 50:
        printable_ratio = sum(1 for c in text if c.isprintable()) / chars
        if printable_ratio > 0.80:
            is_digital = True
            
            # Check font mapping
            try:
                resources = page.get("/Resources", {})
                if resources and "/Font" in resources:
                    fonts = resources["/Font"]
                    font_keys = list(fonts.keys()) if hasattr(fonts, "keys") else []
                    if font_keys:
                        unmapped = 0
                        for k in font_keys:
                            try:
                                font_obj = fonts[k].get_object()
                                encoding = font_obj.get("/Encoding", "")
                                is_std_enc = encoding and any(se in str(encoding) for se in ["WinAnsi", "MacRoman", "StandardEncoding"])
                                if "/ToUnicode" not in font_obj and not is_std_enc:
                                    unmapped += 1
                            except Exception:
                                unmapped += 1
                        if unmapped / len(font_keys) > 0.50:
                            is_digital = False
            except Exception:
                pass

    # Determine type and parser
    # Fast digital check for table using pdfplumber find_tables
    table_detected = False
    if is_digital and PDFPLUMBER_AVAILABLE:
        try:
            if plumber_reader:
                p = plumber_reader.pages[page_index]
                if len(p.rects) + len(p.lines) > 5:
                    table_detected = len(p.find_tables()) > 0
            else:
                import pdfplumber
                with pdfplumber.open(filepath) as pdf:
                    p = pdf.pages[page_index]
                    if len(p.rects) + len(p.lines) > 5:
                        table_detected = len(p.find_tables()) > 0
        except Exception:
            pass

    if is_digital:
        if table_detected:
            return "TABLE", "pdfplumber", 1.0
        else:
            return "DIGITAL", "pypdf", 1.0
    else:
        # Mixed/Scanned
        if chars > 0:
            parser = "pdfplumber" if (table_detected or parse_method_hint == "pdfplumber") else "pypdf"
            return "MIXED", parser, 0.8
        else:
            return "SCANNED", "ocr", 1.0


# ──────────────────────────────────────────────────────────────────────────────
# Memory utility
# ──────────────────────────────────────────────────────────────────────────────
def _rss_mb() -> float:
    try:
        import psutil
        return psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
    except ImportError:
        pass
    try:
        with open("/proc/self/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return float(line.split()[1]) / 1024
            return 0.0
    except Exception:
        pass
    return 0.0


# ──────────────────────────────────────────────────────────────────────────────
# Per-page extraction helpers
# ──────────────────────────────────────────────────────────────────────────────
def _clean_extracted_text(text: str) -> str:
    if not text:
        return ""
    # 1. Replace Unicode replacement character (often a converted hyphen/dash) with standard hyphen
    text = text.replace('\ufffd', '-')
    # 2. Fix kerning/spacing issues where a single capital letter (except A and I) is separated from the rest of the word
    # ONLY merge if the second part is NOT a valid English word in our loaded vocabulary/dictionary (prevents spacing regressions)
    def _replace_kerning(match):
        cap = match.group(1)
        rest = match.group(2)
        if rest.lower() in _VOCAB:
            return match.group(0)
        return cap + rest

    text = re.sub(r'\b([B-HJ-Z])\s+([a-z]{2,})\b', _replace_kerning, text)
    # 3. Standardize other common dash variants to hyphen
    text = re.sub(r'[\u2010\u2011\u2012\u2013\u2014\u2015\u2212]', '-', text)
    # 4. Standardize quotes (curly quotes to straight quotes)
    text = re.sub(r'[\u2018\u2019\u201a\u201b\u2039\u203a]', "'", text)
    text = re.sub(r'[\u201c\u201d\u201e\u201f\u00ab\u00bb]', '"', text)
    # 5. Fix common OCR substitutions: digit 1 vs lowercase L, digit 0 vs letter O
    # Only replace if surrounded by digits to prevent breaking valid text
    text = re.sub(r'(?<=\d)l(?=\d)', '1', text)
    text = re.sub(r'(?<=\d)o(?=\d)', '0', text)
    text = re.sub(r'(?<=\d)O(?=\d)', '0', text)
    # 6. Normalize multiple consecutive spaces to a single space
    text = re.sub(r'[ \t]+', ' ', text)
    return text


def _extract_page_pypdf(reader, page_index: int) -> str:
    """Extract text from a single page using pypdf."""
    try:
        text = reader.pages[page_index].extract_text() or ""
        return _clean_extracted_text(text)
    except Exception as e:
        raise RuntimeError(f"pypdf page {page_index + 1} error: {e}") from e


def _extract_page_pdfplumber(filepath: str, page_index: int) -> str:
    """Extract text from a single page using pdfplumber."""
    import pdfplumber
    try:
        with pdfplumber.open(filepath) as pdf:
            page = pdf.pages[page_index]
            return _clean_extracted_text(page.extract_text() or "")
    except Exception as e:
        raise RuntimeError(f"pdfplumber page {page_index + 1} error: {e}") from e

def _extract_page_pdfplumber_with_tables(filepath: str, page_index: int) -> tuple[str, list[dict]]:
    """Extract text and structured tables from a single page using pdfplumber."""
    import pdfplumber
    try:
        with pdfplumber.open(filepath) as pdf:
            page = pdf.pages[page_index]
            text = _clean_extracted_text(page.extract_text() or "")
            
            # Extract tables
            tables = page.extract_tables()
            extracted_tables = []
            markdown_tables = []
            
            for t_idx, table in enumerate(tables):
                if not table or len(table) == 0:
                    continue
                col_count = len(table[0])
                row_count = len(table)
                
                lines = []
                for row_idx, row in enumerate(table):
                    cleaned_row = [str(cell).replace("\n", " ").strip() if cell is not None else "" for cell in row]
                    lines.append("| " + " | ".join(cleaned_row) + " |")
                    if row_idx == 0:
                        lines.append("|" + "|".join(["---"] * len(cleaned_row)) + "|")
                
                md_table = "\n".join(lines)
                markdown_tables.append(md_table)
                extracted_tables.append({
                    "table_index": t_idx + 1,
                    "row_count": row_count,
                    "column_count": col_count,
                    "markdown": md_table
                })
            
            if markdown_tables:
                text += "\n\n" + "\n\n".join(markdown_tables)
                
            return text, extracted_tables
    except Exception as e:
        raise RuntimeError(f"pdfplumber page {page_index + 1} error: {e}") from e


def _extract_page_ocr(filepath: str, page_index: int, enhanced_pages_path: Optional[str] = None) -> tuple[str, float]:
    """Rasterize a PDF page and run Tesseract OCR on it (uses enhanced images if available)."""
    import pytesseract
    from pdf2image import convert_from_path
    from pytesseract import Output
    import cv2
    try:
        # 1. Try to load from enhanced_pages_path if provided
        if enhanced_pages_path:
            img_path = os.path.join(enhanced_pages_path, f"page_{page_index}.png")
            if os.path.exists(img_path):
                img = cv2.imread(img_path)
                if img is not None:
                    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    data = pytesseract.image_to_data(img_rgb, output_type=Output.DICT)
                    confidences = [float(c) for c in data.get('conf', []) if c is not None and str(c).strip() != '' and float(c) != -1]
                    avg_confidence = sum(confidences) / len(confidences) if confidences else 100.0
                    ocr_text = pytesseract.image_to_string(img_rgb, config="--psm 6")
                    return _clean_extracted_text(ocr_text), avg_confidence

        # 2. Fallback: render original PDF page
        poppler_path = getattr(config, "PREPROCESS_POPPLER_PATH", None) or os.getenv("PREPROCESS_POPPLER_PATH") or None
        images = convert_from_path(
            filepath,
            first_page=page_index + 1,
            last_page=page_index + 1,
            dpi=200,
            poppler_path=poppler_path
        )
        if not images:
            return "", 0.0
            
        data = pytesseract.image_to_data(images[0], output_type=Output.DICT)
        confidences = [float(c) for c in data.get('conf', []) if c is not None and str(c).strip() != '' and float(c) != -1]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 100.0
        ocr_text = pytesseract.image_to_string(images[0], config="--psm 6")
        return _clean_extracted_text(ocr_text), avg_confidence
    except Exception as e:
        raise RuntimeError(f"OCR page {page_index + 1} error: {e}") from e


# ──────────────────────────────────────────────────────────────────────────────
# Main entry point
# ──────────────────────────────────────────────────────────────────────────────
def parse_pdf(
    filepath: str,
    task_id: Optional[str] = None,
    lease_token: Optional[str] = None,
    progress_json: Optional[dict] = None,
    trace_fn: Optional[Callable[[str], None]] = None,
    api_url: Optional[str] = None,
    api_headers: Optional[dict] = None,
    skip_ocr: bool = False,
    document_type: str = "DIGITAL",
    routing_confidence: float = 1.0,
    parse_method_hint: str = "pypdf",
    enhanced_pages_path: Optional[str] = None
) -> ParseResult:
    """
    Parse a PDF file using the method hint determined during preprocessing.
    """
    import pypdf

    def _trace(msg: str):
        logger.info(msg)
        if trace_fn:
            try:
                trace_fn(msg)
            except Exception:
                pass

    # ── validate file ────────────────────────────────────────────────────────
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"PDF file not found: {filepath}")

    file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
    _trace(f"[PARSER] PDF file: {os.path.basename(filepath)} ({file_size_mb:.1f} MB)")
    _trace(f"[PARSER] Capabilities: pdfplumber={'yes' if PDFPLUMBER_AVAILABLE else 'no'}, OCR={'yes' if OCR_AVAILABLE else 'no'}")
    _trace(f"[PARSER] Routing: document_type={document_type} (confidence={routing_confidence:.2f}), parse_method_hint={parse_method_hint}")

    # ── temp dir for checkpoint cache ────────────────────────────────────────
    _worker_dir = os.path.dirname(os.path.abspath(__file__))
    _backend_dir = os.path.dirname(_worker_dir)
    _temp_dir = os.path.join(_backend_dir, "storage", "temp")
    os.makedirs(_temp_dir, exist_ok=True)

    temp_cache_file = os.path.join(_temp_dir, f"temp_parse_{task_id}.txt") if task_id else None

    def _cleanup():
        if temp_cache_file and os.path.exists(temp_cache_file):
            try:
                os.remove(temp_cache_file)
            except Exception:
                pass

    # ── read checkpoint ──────────────────────────────────────────────────────
    checkpoint_page = 0
    if progress_json:
        try:
            p = progress_json if isinstance(progress_json, dict) else {}
            checkpoint_page = int(p.get("checkpoint_page", 0))
        except Exception:
            pass

    # ── open PDF with pypdf to get page count + circuit breaker ─────────────
    t_open_start = time.perf_counter()
    try:
        reader = pypdf.PdfReader(filepath)
    except Exception as e:
        _cleanup()
        err = str(e).lower()
        if any(k in err for k in ("pdf", "read", "corrupt", "decrypt", "eof")):
            raise ValueError(f"FAILED_VALIDATION: Corrupted or unreadable PDF. Details: {e}")
        raise
    t_open_end = time.perf_counter()
    pdf_open_time = t_open_end - t_open_start

    t_page_start = time.perf_counter()
    page_count = len(reader.pages)
    t_page_end = time.perf_counter()
    page_count_discovery_time = t_page_end - t_page_start
    _trace(f"[PARSER] Total pages: {page_count}")

    # Circuit breaker: absurdly high page count for file size
    if page_count > (file_size_mb * 3000) + 100:
        _cleanup()
        raise ValueError(
            f"FAILED_VALIDATION: Anomaly — {page_count} pages for {file_size_mb:.1f} MB file. "
            "Possible structural corruption."
        )

    # Hard page cap
    if page_count > MAX_PAGES:
        _cleanup()
        raise RuntimeError(f"Governance Limit Exceeded: PDF has {page_count} pages (limit is {MAX_PAGES}). Aborting to prevent overload.")

    # ── per-page extraction loop ─────────────────────────────────────────────
    start_time  = time.time()
    text_parts  = []
    pages_list  = []
    page_failures: list[dict] = []
    ocr_pages   = 0
    ocr_confidences = []
    low_text_pages = 0
    plumber_pages  = 0

    pypdf_time = 0.0
    plumber_time = 0.0
    ocr_time = 0.0
    parser_selection_overhead = 0.0

    # Resume from checkpoint
    if checkpoint_page > 0 and temp_cache_file and os.path.exists(temp_cache_file):
        _trace(f"[PARSER] Resuming from checkpoint page {checkpoint_page}")
        with open(temp_cache_file, "r", encoding="utf-8") as f:
            text_parts.append(f.read())
    elif temp_cache_file and os.path.exists(temp_cache_file):
        _cleanup()

    # Pre-open pdfplumber if available to avoid opening it repeatedly in page-level loops
    plumber_reader = None
    if PDFPLUMBER_AVAILABLE:
        try:
            import pdfplumber
            plumber_reader = pdfplumber.open(filepath)
        except Exception:
            pass

    _trace(f"[PARSER] Extraction started — processing {page_count - checkpoint_page} pages under page-level routing rules")

    for i in range(checkpoint_page, page_count):
        # ── timeout guard ────────────────────────────────────────────────────
        elapsed = time.time() - start_time
        if elapsed > PARSE_TIMEOUT_S:
            if plumber_reader:
                try: plumber_reader.close()
                except Exception: pass
            _cleanup()
            raise TimeoutError(f"PDF parse timeout exceeded ({PARSE_TIMEOUT_S}s) at page {i + 1}")

        # ── memory guard (every N pages) ─────────────────────────────────────
        if (i - checkpoint_page) % MEMORY_CHECK_EVERY == 0 and i > checkpoint_page:
            rss = _rss_mb()
            if rss > MEMORY_LIMIT_MB:
                _trace(f"[PARSER] MEMORY GUARD: {rss:.0f} MB RSS at page {i + 1} — raising error to prevent OOM")
                if plumber_reader:
                    try: plumber_reader.close()
                    except Exception: pass
                _cleanup()
                raise MemoryError(f"Governance Limit Exceeded: Parser memory usage ({rss:.0f} MB) exceeded limit ({MEMORY_LIMIT_MB} MB).")

        # ── page-level heuristics and features ───────────────────────────────
        t_route_start = time.perf_counter()
        
        detected_type, chosen_parser, route_conf = _determine_page_routing_and_type(
            reader, i, filepath, parse_method_hint, plumber_reader
        )
        
        img = None
        table_detected = False
        contains_signature = False
        contains_handwriting = False
        
        # Only render page thumbnail if it is scanned / requires OCR
        if chosen_parser == "ocr":
            img = _render_page_thumbnail(filepath, i)
            if img:
                try:
                    table_detected = _detect_table(img)
                    contains_signature = _detect_signature(img)
                    contains_handwriting = _compute_handwriting_score(img) > 0.4
                except Exception:
                    pass
        else:
            table_detected = (detected_type == "TABLE")

        page_text = ""
        used_parser = ""
        ocr_conf = 0.0
        page_tables_metadata = []

        if chosen_parser == "ocr" and OCR_AVAILABLE:
            t_sub_start = time.perf_counter()
            try:
                ocr_text_page, ocr_conf_val = _extract_page_ocr(filepath, i, enhanced_pages_path)
                page_text = ocr_text_page
                used_parser = "ocr"
                ocr_conf = ocr_conf_val
                ocr_pages += 1
                ocr_confidences.append(ocr_conf)
            except Exception as e:
                page_failures.append({"page": i + 1, "parser": "ocr", "reason": str(e)})
                used_parser = "pypdf"
                try:
                    page_text = _extract_page_pypdf(reader, i)
                except Exception:
                    pass
            ocr_time += time.perf_counter() - t_sub_start
        elif chosen_parser == "pdfplumber" and PDFPLUMBER_AVAILABLE:
            t_sub_start = time.perf_counter()
            try:
                page_text, page_tables_metadata = _extract_page_pdfplumber_with_tables(filepath, i)
                used_parser = "pdfplumber"
                plumber_pages += 1
            except Exception as e:
                page_failures.append({"page": i + 1, "parser": "pdfplumber", "reason": str(e)})
                used_parser = "pypdf"
                try:
                    page_text = _extract_page_pypdf(reader, i)
                except Exception:
                    pass
            plumber_time += time.perf_counter() - t_sub_start
        else:
            t_sub_start = time.perf_counter()
            try:
                page_text = _extract_page_pypdf(reader, i)
                used_parser = "pypdf"
            except Exception as e:
                page_failures.append({"page": i + 1, "parser": "pypdf", "reason": str(e)})
            pypdf_time += time.perf_counter() - t_sub_start

        # Page-level OCR fallback: if the extracted digital text is too short, route to OCR
        chars = len(page_text.strip())
        if used_parser in ("pypdf", "pdfplumber") and chars < LOW_TEXT_THRESH and OCR_AVAILABLE:
            _trace(f"[PARSER] Page {i + 1} yielded only {chars} chars digitally (below threshold {LOW_TEXT_THRESH}). Routing to OCR fallback.")
            t_sub_start = time.perf_counter()
            try:
                ocr_text_page, ocr_conf_val = _extract_page_ocr(filepath, i, enhanced_pages_path)
                page_text = ocr_text_page
                used_parser = "ocr"
                ocr_conf = ocr_conf_val
                ocr_pages += 1
                ocr_confidences.append(ocr_conf)
            except Exception as e:
                page_failures.append({"page": i + 1, "parser": "ocr_fallback", "reason": str(e)})
            ocr_time += time.perf_counter() - t_sub_start

        parser_selection_overhead += time.perf_counter() - t_route_start
        
        # Log the routing decision per page
        _trace(f"[PAGE ROUTING] Page {i+1} - Detected Type: {detected_type} | Chosen Parser: {used_parser} | Extracted Characters: {len(page_text)} | Confidence: {ocr_conf if used_parser == 'ocr' else route_conf}")

        if page_text:
            text_parts.append(page_text)

        # Store page-level data
        pages_list.append({
            "page_number": i + 1,
            "text": page_text,
            "extraction_method": used_parser,
            "ocr_engine": "tesseract" if used_parser == "ocr" else "none",
            "ocr_confidence": ocr_conf,
            "table_detected": table_detected or len(page_tables_metadata) > 0,
            "contains_signature": contains_signature,
            "contains_handwriting": contains_handwriting,
            "tables": page_tables_metadata,
        })

        # ── character limit guard ────────────────────────────────────────────
        current_chars = sum(len(part) for part in text_parts)
        if current_chars > config.MAX_CHARACTER_LIMIT:
            _trace(f"[PARSER] CHARACTER LIMIT GUARD: {current_chars:,} characters parsed at page {i + 1} — raising error to prevent OOM")
            if plumber_reader:
                try: plumber_reader.close()
                except Exception: pass
            _cleanup()
            raise ValueError(f"Governance Limit Exceeded: Document text size ({current_chars:,} chars) exceeded limit ({config.MAX_CHARACTER_LIMIT:,} chars).")

        # ── checkpoint write (every 10 pages) ─────────────────────────────────
        if temp_cache_file and (i + 1) % 10 == 0:
            try:
                with open(temp_cache_file, "w", encoding="utf-8") as f:
                    f.write("\n\n".join(text_parts))
            except Exception:
                pass

        # ── progress PATCH (every 10 pages, if connected to API) ─────────────
        if task_id and lease_token and api_url and (i + 1) % 10 == 0:
            rss = _rss_mb()
            try:
                import requests as _requests
                _requests.patch(
                    f"{api_url}/tasks/{task_id}/progress",
                    json={
                        "worker_id":       os.getenv("WORKER_ID", "worker-1"),
                        "lease_token":     lease_token,
                        "checkpoint_page": i + 1,
                        "total_pages":     page_count,
                        "memory_mb":       round(rss, 2),
                        "status":          "running",
                        "pages_processed": i + 1 - checkpoint_page,
                    },
                    headers=api_headers or {},
                    timeout=5,
                )
            except Exception as ex:
                logger.warning(f"Progress PATCH failed: {ex}")

    if plumber_reader:
        try:
            plumber_reader.close()
        except Exception:
            pass

    # ── assemble final text ───────────────────────────────────────────────────
    full_text = "\n\n".join(text_parts)
    _cleanup()

    duration = round(time.time() - start_time, 2)
    stats = {
        "parser":          "pypdf"  # primary used
                           if plumber_pages == 0 and ocr_pages == 0
                           else ("pdfplumber_fallback" if plumber_pages > 0 and ocr_pages == 0
                                 else "ocr_fallback"),
        "total_pages":     page_count,
        "processed_pages": page_count - checkpoint_page,
        "low_text_pages":  low_text_pages,
        "pdfplumber_pages": plumber_pages,
        "ocr_pages":       ocr_pages,
        "ocr_confidences": ocr_confidences,
        "avg_ocr_confidence": sum(ocr_confidences) / len(ocr_confidences) if ocr_confidences else 100.0,
        "char_count":      len(full_text),
        "duration_seconds": duration,
        "page_failures":   page_failures,
        "pdfplumber_available": PDFPLUMBER_AVAILABLE,
        "ocr_available":   OCR_AVAILABLE,
        "ocr_attempted":   False,
        "initial_parser":  parse_method_hint,
        "comparison_metrics": {
            "pypdf_score": 100.0,
            "ocr_score": 100.0,
            "selected_parser": parse_method_hint,
            "rejection_reason": "",
            "pypdf_printable_ratio": 1.0,
            "ocr_printable_ratio": 1.0,
            "pypdf_ocr_confidence": 100.0,
            "ocr_ocr_confidence": 100.0,
            "pypdf_coherence_score": 100.0,
            "ocr_coherence_score": 100.0,
            "pypdf_dict_word_ratio": 1.0,
            "ocr_dict_word_ratio": 1.0
        },
        "timings": {
            "pdf_open_time": round(pdf_open_time, 5),
            "page_count_discovery_time": round(page_count_discovery_time, 5),
            "pypdf_extraction_duration": round(pypdf_time, 5),
            "pdfplumber_extraction_duration": round(plumber_time, 5),
            "ocr_duration": round(ocr_time, 5),
            "parser_selection_overhead": round(parser_selection_overhead, 5),
            "parse_quality_evaluation_duration": 0.0,
            "ocr_rescue_quality_evaluation_duration": 0.0
        }
    }

    _trace(
        f"[PARSER] Complete — {stats['processed_pages']} pages in {duration}s | "
        f"chars={stats['char_count']} | pdfplumber_pages={plumber_pages} | ocr_pages={stats['ocr_pages']} | "
        f"failures={len(page_failures)}"
    )

    return ParseResult(text=full_text, stats=stats, pages=pages_list)
