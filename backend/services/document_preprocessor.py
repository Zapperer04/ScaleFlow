"""
document_preprocessor.py — Pre-parse document quality evaluation and enhancement.

Stage position in the pipeline:
    Upload → preprocess_document → parse_document → validate_parse_quality → ...

Responsibilities:
  1. Evaluate quality signals on sampled pages (blur, DPI, contrast, skew, noise)
  2. Detect content types: text, handwriting, signatures, tables, image regions
  3. Apply image enhancement when quality is below configured thresholds
  4. Hard-reject only: encrypted PDFs, corrupted PDFs
  5. Optionally reject heavily handwritten documents (opt-in via PREPROCESS_REJECT_HANDWRITTEN)

Public API:
  evaluate_document(filepath, trace_fn) -> PreprocessingReport
  enhance_document(filepath, report, pipeline_id, output_dir, trace_fn) -> str (output path)

The two functions are intentionally separate:
  - evaluate_document() is fast (< 5s), works on sampled pages only, and always runs.
  - enhance_document() only runs if report.needs_enhancement is True.

Output path convention:
  The enhanced PDF is written to output_dir/preprocessed_{pipeline_id}.pdf.
  This path is NOT stored inside PreprocessingReport (it is ephemeral runtime state).
  handle_parse_document() recovers it by the same convention.
"""

from __future__ import annotations

import os
import time
import logging
from dataclasses import dataclass, field
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


# ─────────────────────────────────────────────────────────────────────────────
# PreprocessingReport — serializable, no filesystem paths
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PreprocessingReport:
    # PDF structure
    is_encrypted: bool
    is_corrupted: bool
    page_count: int

    # Image quality scores (0–100, higher = better)
    blur_score: float           # 0 = very blurry, 100 = sharp (Laplacian variance)
    contrast_score: float       # 0 = flat, 100 = high contrast (RMS contrast)
    skew_angle: float           # degrees, 0 = straight
    noise_score: float          # 0 = very noisy, 100 = clean (local variance)

    # DPI estimate — None when no embedded raster images are found
    # (typical for vector PDFs and browser-printed PDFs).
    # When None: excluded from needs_enhancement check and overall_quality composite.
    dpi_estimate: Optional[float]

    # Derived quality gate
    needs_enhancement: bool     # True if any measurable score is below its threshold
    overall_quality: float      # 0–100 composite (DPI excluded if None)

    # Text content
    extractable_text_ratio: float   # fraction of sampled pages with >LOW_TEXT_THRESH chars

    # Content flags (informational — logged in trace, stored in artifact)
    # None of these cause rejection except is_heavily_handwritten (opt-in only).
    has_handwriting: bool
    has_signature: bool
    has_table: bool

    # NOTE: has_image_region means "a significant non-text image region was detected".
    # This could be a photo, chart, diagram, logo, watermark, or stamp.
    # Chart-specific classification requires an ML model and is out of scope here.
    has_image_region: bool

    # Handwriting severity
    handwriting_score: float        # 0–1 composite handwriting confidence
    is_heavily_handwritten: bool    # True when score >= HW_SCORE_MIN AND text_ratio < HW_TEXT_RATIO_MAX
                                    # Rejection is opt-in via PREPROCESS_REJECT_HANDWRITTEN

    # Accumulated warnings (non-fatal issues found during evaluation)
    warnings: List[str] = field(default_factory=list)

    # Evaluation metadata
    sampled_pages: List[int] = field(default_factory=list)
    evaluation_duration_ms: float = 0.0
    enhancement_duration_ms: float = 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Library probes — graceful degradation when optional deps are absent
# ─────────────────────────────────────────────────────────────────────────────

def _probe_cv2() -> bool:
    try:
        import cv2  # noqa: F401
        return True
    except ImportError:
        return False


def _probe_pdf2image() -> bool:
    """
    Returns True only if both the pdf2image Python library AND the Poppler
    binary (pdftoppm) are available. The library can import cleanly even when
    Poppler is not installed; the render will fail at runtime without the binary.
    """
    try:
        from pdf2image import convert_from_path  # noqa: F401
        from pdf2image.pdf2image import pdfinfo_from_path
        import tempfile, os
        poppler_path = None
        try:
            if getattr(config, "PREPROCESS_POPPLER_PATH", None):
                poppler_path = config.PREPROCESS_POPPLER_PATH
        except Exception:
            pass
        if not poppler_path:
            poppler_path = os.getenv("PREPROCESS_POPPLER_PATH")

        # Verify Poppler binary resolves — use a dummy path; the error we care
        # about is PDFInfoNotInstalledError, not "file not found".
        try:
            pdfinfo_from_path(os.devnull, poppler_path=poppler_path)
        except Exception as e:
            if "poppler" in str(e).lower() or "pdfinfo" in str(e).lower() or "installed" in str(e).lower():
                return False
            # Any other error means Poppler is present but the file is invalid — that's fine
        return True
    except ImportError:
        return False


CV2_AVAILABLE = _probe_cv2()
PDF2IMAGE_AVAILABLE = _probe_pdf2image()


def _get_poppler_path() -> Optional[str]:
    """
    Return the Poppler binary directory if configured, else None (use PATH).
    Set PREPROCESS_POPPLER_PATH in .env or environment to the directory that
    contains pdftoppm.exe (Windows) when Poppler is not on the system PATH.
    Example: C:\\Users\\you\\poppler\\Library\\bin
    """
    path = getattr(config, 'PREPROCESS_POPPLER_PATH', '').strip()
    return path if path else None


# ─────────────────────────────────────────────────────────────────────────────
# Page sampling
# ─────────────────────────────────────────────────────────────────────────────

def _select_sample_pages(page_count: int, max_samples: int) -> List[int]:
    """
    Select a representative sample of page indices without reading the whole doc.
    Always includes the first page, last page, and evenly distributed middle pages.
    """
    if page_count <= max_samples:
        return list(range(page_count))
    samples: set[int] = {0, page_count - 1}
    step = max(1, page_count // (max_samples - 1))
    for i in range(step, page_count - 1, step):
        samples.add(i)
        if len(samples) >= max_samples:
            break
    return sorted(samples)


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — PDF structural probe (no rendering, fast)
# ─────────────────────────────────────────────────────────────────────────────

def _inspect_pdf_structure(filepath: str) -> dict:
    """
    Inspect PDF structural metadata using pypdf.
    No pages are rendered — this is purely a structural read.

    DPI estimation uses /MediaBox width vs embedded image /Width.
    This only works when the PDF contains embedded raster images.
    For vector PDFs or browser-printed PDFs, dpi_estimate is set to None
    and must be excluded from all quality checks downstream.
    """
    import pypdf

    result: dict = {
        "page_count": 0,
        "is_encrypted": False,
        "is_corrupted": False,
        "image_count_sampled": 0,
        "dpi_estimate": None,  # None = no embedded raster images found
    }

    try:
        reader = pypdf.PdfReader(filepath, strict=False)
        result["is_encrypted"] = reader.is_encrypted
        if reader.is_encrypted:
            return result
        result["page_count"] = len(reader.pages)
    except Exception as exc:
        err = str(exc).lower()
        if any(k in err for k in ("corrupt", "eof", "xref", "invalid", "malformed", "pdf")):
            result["is_corrupted"] = True
        return result

    # DPI estimation — best-effort, only valid when embedded raster images exist
    dpi_values: list[float] = []
    sample_size = min(3, result["page_count"])
    try:
        for i in range(sample_size):
            page = reader.pages[i]
            resources = page.get("/Resources")
            if not resources:
                continue
            xobj = resources.get("/XObject")
            if not xobj:
                continue
            for key in xobj:
                obj = xobj[key]
                if obj.get("/Subtype") == "/Image":
                    result["image_count_sampled"] += 1
                    img_width = obj.get("/Width")
                    media_box = page.mediabox
                    if img_width and media_box:
                        page_width_pts = float(media_box.width)   # 1 pt = 1/72 inch
                        page_width_inches = page_width_pts / 72.0
                        if page_width_inches > 0:
                            dpi_values.append(float(img_width) / page_width_inches)
    except Exception:
        pass  # DPI estimation is best-effort; failure is non-fatal

    if dpi_values:
        result["dpi_estimate"] = round(sum(dpi_values) / len(dpi_values), 1)
    # If dpi_values is empty: dpi_estimate stays None

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Quick text probe (no rendering, fast)
# ─────────────────────────────────────────────────────────────────────────────

def _probe_text(filepath: str, sampled_pages: List[int]) -> dict:
    """
    Use pypdf to extract text from sampled pages only.
    Measures what fraction of pages yield usable text without OCR.
    Reuses the same LOW_TEXT_CHARS threshold from the main parser config.
    """
    import pypdf
    low_text_thresh = config.PDF_LOW_TEXT_CHARS
    pages_with_text = 0
    total_chars = 0

    try:
        reader = pypdf.PdfReader(filepath, strict=False)
        for i in sampled_pages:
            if i >= len(reader.pages):
                continue
            try:
                txt = reader.pages[i].extract_text() or ""
                chars = len(txt.strip())
                total_chars += chars
                if chars >= low_text_thresh:
                    pages_with_text += 1
            except Exception:
                pass
    except Exception:
        pass

    n = max(len(sampled_pages), 1)
    return {
        "extractable_text_ratio": pages_with_text / n,
        "avg_chars_per_page": total_chars / n,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 — Image-level signal computation helpers
# ─────────────────────────────────────────────────────────────────────────────

def _render_page_thumbnail(filepath: str, page_index: int, dpi: int = 72):
    """Render a single PDF page to a PIL Image at the given DPI."""
    from pdf2image import convert_from_path
    imgs = convert_from_path(
        filepath,
        first_page=page_index + 1,
        last_page=page_index + 1,
        dpi=dpi,
        poppler_path=_get_poppler_path(),
    )
    return imgs[0] if imgs else None


def _compute_blur_score(gray) -> float:
    """
    Laplacian variance method. Higher variance = sharper.
    Returns 0–100 (0=very blurry, 100=sharp).
    Calibration: Laplacian var ~500 on a clean printed page → score 100.
    """
    import cv2
    lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    return min(float(lap_var) / 5.0, 100.0)


def _compute_contrast_score(gray) -> float:
    """
    RMS contrast. Returns 0–100 (0=flat/washed-out, 100=high contrast).
    Calibration: RMS 0.30 on a typical printed page → score 100.
    """
    import numpy as np
    f = gray.astype(float) / 255.0
    rms = float(np.sqrt(np.mean((f - f.mean()) ** 2)))
    return min(rms / 0.3 * 100.0, 100.0)


def _compute_skew_angle(gray) -> float:
    """
    Hough transform line detection to estimate page skew in degrees.
    Positive angle = counter-clockwise tilt (rotate clockwise to correct).
    Returns 0.0 if no reliable line set is detected.
    """
    import cv2
    import numpy as np
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLines(edges, 1, np.pi / 180, threshold=80)
    if lines is None:
        return 0.0
    angles = []
    for line in lines[:50]:
        _, theta = line[0]
        angle = (theta * 180.0 / np.pi) - 90.0
        if abs(angle) < 45:
            angles.append(angle)
    return float(np.median(angles)) if angles else 0.0


def _compute_noise_score(gray) -> float:
    """
    Local pixel variance method.
    High local variance in otherwise uniform regions indicates noise.
    Returns 0–100 (0=very noisy, 100=clean).
    """
    import cv2
    import numpy as np
    kernel = np.ones((5, 5), np.float32) / 25
    local_mean = cv2.filter2D(gray.astype(float), -1, kernel)
    local_var = cv2.filter2D(gray.astype(float) ** 2, -1, kernel) - local_mean ** 2
    noise_level = min(float(local_var.mean()) / 500.0, 1.0)
    return round((1.0 - noise_level) * 100.0, 1)


def _compute_handwriting_score(img) -> float:
    """
    Heuristic handwriting detection via image texture analysis.
    No ML model — uses structural properties of ink strokes.

    Handwritten text characteristics:
      - Irregular stroke widths (typed fonts are nearly uniform)
      - High variance in connected-component sizes
      - Spatially uneven ink density

    Returns 0–1 (0 = clearly typed, 1 = clearly handwritten).
    """
    import cv2
    import numpy as np

    gray = np.array(img.convert("L"))
    binary = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        11, 2,
    )

    # Signal 1: stroke width variance via distance transform
    dist = cv2.distanceTransform(binary, cv2.DIST_L2, 5)
    ink_pixels = dist[binary > 0]
    sw_score = min(float(ink_pixels.std()) / 3.0, 1.0) if len(ink_pixels) > 0 else 0.0

    # Signal 2: connected-component size coefficient of variation
    _, _, stats, _ = cv2.connectedComponentsWithStats(binary)
    areas = stats[1:, cv2.CC_STAT_AREA]  # skip background label 0
    cc_score = 0.0
    if len(areas) > 1:
        cv_ratio = float(areas.std()) / (float(areas.mean()) + 1e-6)
        cc_score = min(cv_ratio / 5.0, 1.0)

    # Signal 3: spatial ink density irregularity
    block_means: list[float] = []
    bh, bw = gray.shape
    bs = 32
    for y in range(0, bh - bs, bs):
        for x in range(0, bw - bs, bs):
            block_means.append(float(gray[y:y + bs, x:x + bs].mean()))
    density_score = 0.0
    if block_means:
        density_score = min(float(np.std(block_means)) / 255.0 * 4.0, 1.0)

    return sw_score * 0.5 + cc_score * 0.3 + density_score * 0.2


def _detect_signature(img) -> bool:
    """
    Signature heuristic: isolated ink blob in the bottom 30% of the page
    with a curvilinear (low-circularity) contour.
    """
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
        # Low circularity = irregular/curvy = signature-like
        if 0.01 < circularity < 0.5 and area < (w * h * 0.30 * 0.25):
            return True
    return False


def _detect_table(img) -> bool:
    """
    Table heuristic: dense grid of horizontal and vertical lines detected
    via Probabilistic Hough Transform.
    Requires at least 3 horizontal and 2 vertical lines to flag as table.
    """
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


def _detect_image_region(img) -> bool:
    """
    Detects presence of a significant non-text image region.

    NOTE: This heuristic only tells you that a large non-text region exists.
    It cannot distinguish between a photo, chart, diagram, logo, watermark,
    or stamp. Those distinctions require an ML classification model and are
    out of scope for this preprocessing stage.

    Returns True if a connected region covering > 5% of the page is found
    that is too large to be a character or text block.
    """
    import cv2
    import numpy as np

    gray = np.array(img.convert("L"))
    h, w = gray.shape
    _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    _, _, stats, _ = cv2.connectedComponentsWithStats(binary)
    page_area = h * w
    for i in range(1, len(stats)):  # skip background
        area = stats[i, cv2.CC_STAT_AREA]
        comp_h = stats[i, cv2.CC_STAT_HEIGHT]
        comp_w = stats[i, cv2.CC_STAT_WIDTH]
        if area > page_area * 0.05 and comp_h > 30 and comp_w > 30:
            return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 — Aggregate image analysis across sampled pages
# ─────────────────────────────────────────────────────────────────────────────

def _analyze_pages(filepath: str, sampled_pages: List[int], trace_fn=None) -> dict:
    """
    Render sampled page thumbnails at 72 DPI and compute all image-level signals.
    Scores are averaged across sampled pages; boolean flags are OR'd (any page triggers).
    """
    def _t(msg: str):
        logger.info(msg)
        if trace_fn:
            try:
                trace_fn(msg)
            except Exception:
                pass

    blur_scores: list[float] = []
    contrast_scores: list[float] = []
    skew_angles: list[float] = []
    noise_scores: list[float] = []
    handwriting_scores: list[float] = []
    has_signature = has_table = has_image_region = False

    for page_idx in sampled_pages[:config.PREPROCESS_SAMPLE_PAGES]:
        try:
            img = _render_page_thumbnail(filepath, page_idx, dpi=72)
            if img is None:
                continue
            import numpy as np
            gray = np.array(img.convert("L"))

            blur_scores.append(_compute_blur_score(gray))
            contrast_scores.append(_compute_contrast_score(gray))
            skew_angles.append(_compute_skew_angle(gray))
            noise_scores.append(_compute_noise_score(gray))
            handwriting_scores.append(_compute_handwriting_score(img))

            if not has_signature:
                has_signature = _detect_signature(img)
            if not has_table:
                has_table = _detect_table(img)
            if not has_image_region:
                has_image_region = _detect_image_region(img)

        except Exception as exc:
            _t(f"[PREPROCESS] WARNING: Image analysis failed on page {page_idx + 1}: {exc}")

    def _avg(lst: list) -> float:
        return round(sum(lst) / len(lst), 2) if lst else 0.0

    avg_hw = _avg(handwriting_scores)
    return {
        "blur_score":        _avg(blur_scores),
        "contrast_score":    _avg(contrast_scores),
        "skew_angle":        _avg(skew_angles),
        "noise_score":       _avg(noise_scores),
        "handwriting_score": avg_hw,
        "has_handwriting":   avg_hw > 0.4,
        "has_signature":     has_signature,
        "has_table":         has_table,
        "has_image_region":  has_image_region,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Scoring helpers
# ─────────────────────────────────────────────────────────────────────────────

def _compute_needs_enhancement(
    blur_score: float,
    contrast_score: float,
    skew_angle: float,
    noise_score: float,
    dpi_estimate: Optional[float],
) -> bool:
    """
    Determine if any enhancement pass is warranted.
    DPI is excluded from this check when dpi_estimate is None
    (no embedded raster images found — vector PDF is fine as-is).
    """
    if blur_score < config.PREPROCESS_BLUR_MIN:
        return True
    if contrast_score < config.PREPROCESS_CONTRAST_MIN:
        return True
    if abs(skew_angle) > config.PREPROCESS_SKEW_MAX_DEG:
        return True
    if noise_score < config.PREPROCESS_NOISE_MIN:
        return True
    if dpi_estimate is not None and dpi_estimate < config.PREPROCESS_DPI_MIN:
        return True
    return False


def _compute_overall_quality(
    blur_score: float,
    contrast_score: float,
    noise_score: float,
    dpi_estimate: Optional[float],
    extractable_text_ratio: float,
) -> float:
    """
    Composite quality score 0–100.
    DPI is excluded from the composite when dpi_estimate is None.
    Weights are adjusted to still sum to 1.0 in the DPI-absent case.
    """
    if dpi_estimate is not None:
        dpi_norm = min(dpi_estimate / max(config.PREPROCESS_DPI_MIN, 1.0) * 100.0, 100.0)
        score = (
            blur_score                   * 0.20 +
            contrast_score               * 0.15 +
            noise_score                  * 0.15 +
            extractable_text_ratio * 100 * 0.30 +
            dpi_norm                     * 0.20
        )
    else:
        score = (
            blur_score                   * 0.25 +
            contrast_score               * 0.20 +
            noise_score                  * 0.20 +
            extractable_text_ratio * 100 * 0.35
        )
    return round(min(score, 100.0), 1)


# ─────────────────────────────────────────────────────────────────────────────
# Public API — evaluate_document
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_document(filepath: str, trace_fn: Optional[Callable] = None) -> PreprocessingReport:
    """
    Evaluate a document's quality and content type before parsing begins.

    Operates on a small sample of pages (PREPROCESS_SAMPLE_PAGES) to stay fast.
    Expected execution time: < 3s for typical documents, < 5s maximum.

    Returns a PreprocessingReport dataclass with quality scores, content flags,
    and a needs_enhancement decision. Does NOT modify the file.
    """
    t_start = time.perf_counter()
    warnings: List[str] = []

    def _t(msg: str):
        logger.info(msg)
        if trace_fn:
            try:
                trace_fn(msg)
            except Exception:
                pass

    _t("[PREPROCESS] Starting document evaluation")

    # ── Phase 1: Structural probe ─────────────────────────────────────────────
    struct = _inspect_pdf_structure(filepath)
    page_count    = struct["page_count"]
    is_encrypted  = struct["is_encrypted"]
    is_corrupted  = struct["is_corrupted"]
    dpi_estimate  = struct["dpi_estimate"]

    if dpi_estimate is None and not is_encrypted and not is_corrupted and page_count > 0:
        warnings.append(
            "DPI could not be estimated — no embedded raster images found in sampled pages. "
            "This is normal for vector PDFs and browser-printed PDFs. "
            "DPI check is excluded from quality scoring."
        )

    # Return early on hard structural failures (still a complete report)
    if is_encrypted or is_corrupted or page_count == 0:
        reason = (
            "encrypted" if is_encrypted
            else "corrupted" if is_corrupted
            else "zero pages"
        )
        _t(f"[PREPROCESS] Early exit: document is {reason}")
        return PreprocessingReport(
            is_encrypted=is_encrypted,
            is_corrupted=is_corrupted,
            page_count=page_count,
            blur_score=0.0,
            contrast_score=0.0,
            skew_angle=0.0,
            noise_score=0.0,
            dpi_estimate=dpi_estimate,
            needs_enhancement=False,
            overall_quality=0.0,
            extractable_text_ratio=0.0,
            has_handwriting=False,
            has_signature=False,
            has_table=False,
            has_image_region=False,
            handwriting_score=0.0,
            is_heavily_handwritten=False,
            warnings=warnings,
            sampled_pages=[],
            evaluation_duration_ms=round((time.perf_counter() - t_start) * 1000, 1),
        )

    # ── Phase 2: Page sampling ────────────────────────────────────────────────
    sampled_pages = _select_sample_pages(page_count, config.PREPROCESS_SAMPLE_PAGES)
    _t(f"[PREPROCESS] Sampling pages: {[p + 1 for p in sampled_pages]} of {page_count} total")

    # ── Phase 3: Text probe ───────────────────────────────────────────────────
    text_info = _probe_text(filepath, sampled_pages)
    extractable_text_ratio = text_info["extractable_text_ratio"]
    _t(f"[PREPROCESS] Extractable text ratio: {extractable_text_ratio:.1%}")

    # ── Phase 4: Image quality analysis (conditional on library availability) ─
    blur_score = contrast_score = noise_score = 100.0
    skew_angle = handwriting_score = 0.0
    has_handwriting = has_signature = has_table = has_image_region = False

    if CV2_AVAILABLE and PDF2IMAGE_AVAILABLE:
        img_signals = _analyze_pages(filepath, sampled_pages, trace_fn=trace_fn)
        blur_score        = img_signals["blur_score"]
        contrast_score    = img_signals["contrast_score"]
        skew_angle        = img_signals["skew_angle"]
        noise_score       = img_signals["noise_score"]
        handwriting_score = img_signals["handwriting_score"]
        has_handwriting   = img_signals["has_handwriting"]
        has_signature     = img_signals["has_signature"]
        has_table         = img_signals["has_table"]
        has_image_region  = img_signals["has_image_region"]

        _t(
            f"[PREPROCESS] Quality signals — "
            f"blur={blur_score:.1f} contrast={contrast_score:.1f} "
            f"skew={skew_angle:.2f}° noise={noise_score:.1f} "
            f"dpi={dpi_estimate if dpi_estimate else 'n/a (vector)'}"
        )
        if has_handwriting:
            _t(f"[PREPROCESS] Handwriting detected (score={handwriting_score:.2f})")
        if has_signature:
            _t("[PREPROCESS] Signature region detected (bottom 30% of at least one page)")
        if has_table:
            _t("[PREPROCESS] Table/grid structure detected")
        if has_image_region:
            _t("[PREPROCESS] Non-text image region detected (photo/diagram/logo/watermark/stamp)")
    else:
        warnings.append(
            "OpenCV or pdf2image is not installed — image quality analysis skipped. "
            "Install opencv-python-headless and pdf2image for full preprocessing support."
        )
        _t("[PREPROCESS] WARNING: Image analysis skipped (opencv/pdf2image unavailable)")

    # ── Phase 5: Derive enhancement need and composite quality ────────────────
    needs_enhancement = _compute_needs_enhancement(
        blur_score, contrast_score, skew_angle, noise_score, dpi_estimate
    )
    overall_quality = _compute_overall_quality(
        blur_score, contrast_score, noise_score, dpi_estimate, extractable_text_ratio
    )

    # ── Phase 6: Heavily handwritten flag ─────────────────────────────────────
    is_heavily_handwritten = (
        handwriting_score >= config.PREPROCESS_HW_SCORE_MIN
        and extractable_text_ratio < config.PREPROCESS_HW_TEXT_RATIO_MAX
    )
    if is_heavily_handwritten:
        _t(
            f"[PREPROCESS] WARNING: Document is heavily handwritten "
            f"(hw_score={handwriting_score:.2f}, text_ratio={extractable_text_ratio:.1%}). "
            f"Rejection is {'enabled' if config.PREPROCESS_REJECT_HANDWRITTEN else 'disabled'} "
            f"(PREPROCESS_REJECT_HANDWRITTEN={config.PREPROCESS_REJECT_HANDWRITTEN})."
        )

    duration_ms = round((time.perf_counter() - t_start) * 1000, 1)
    _t(
        f"[PREPROCESS] Evaluation complete — "
        f"quality={overall_quality:.1f}/100 "
        f"needs_enhancement={needs_enhancement} "
        f"({duration_ms:.0f}ms)"
    )

    return PreprocessingReport(
        is_encrypted=is_encrypted,
        is_corrupted=is_corrupted,
        page_count=page_count,
        blur_score=blur_score,
        contrast_score=contrast_score,
        skew_angle=skew_angle,
        noise_score=noise_score,
        dpi_estimate=dpi_estimate,
        needs_enhancement=needs_enhancement,
        overall_quality=overall_quality,
        extractable_text_ratio=extractable_text_ratio,
        has_handwriting=has_handwriting,
        has_signature=has_signature,
        has_table=has_table,
        has_image_region=has_image_region,
        handwriting_score=handwriting_score,
        is_heavily_handwritten=is_heavily_handwritten,
        warnings=warnings,
        sampled_pages=sampled_pages,
        evaluation_duration_ms=duration_ms,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Enhancement helpers
# ─────────────────────────────────────────────────────────────────────────────

def _apply_deskew(img, angle: float):
    """Rotate the page image to correct skew. Expands canvas to avoid cropping."""
    return img.rotate(-angle, expand=True, fillcolor=(255, 255, 255))


def _apply_upscale(img, source_dpi: int, target_dpi: int):
    """Lanczos upscale from source_dpi to target_dpi resolution."""
    from PIL import Image
    scale = target_dpi / max(source_dpi, 1)
    new_size = (int(img.width * scale), int(img.height * scale))
    return img.resize(new_size, Image.LANCZOS)


def _apply_denoise(img):
    """
    Gaussian denoising via OpenCV fastNlMeansDenoising.

    PERFORMANCE WARNING: cv2.fastNlMeansDenoising is slow on large images.
    At 300 DPI, a single A4 page (~2480×3508 px) can take 3–8 seconds.
    For documents with many pages, this is the dominant cost in enhancement.
    Benchmark with real production file sizes before enabling at scale.
    Consider cv2.GaussianBlur as a faster (but weaker) alternative for high-
    throughput environments.
    """
    import cv2
    import numpy as np
    from PIL import Image
    gray = np.array(img.convert("L"))
    denoised = cv2.fastNlMeansDenoising(gray, h=10, templateWindowSize=7, searchWindowSize=21)
    return Image.fromarray(denoised).convert("RGB")


def _apply_contrast(img):
    """CLAHE (Contrast-Limited Adaptive Histogram Equalization) enhancement."""
    import cv2
    import numpy as np
    from PIL import Image
    gray = np.array(img.convert("L"))
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    return Image.fromarray(enhanced).convert("RGB")


def _apply_sharpen(img):
    """Unsharp mask sharpening to recover detail lost to blur."""
    from PIL import ImageFilter
    return img.filter(ImageFilter.UnsharpMask(radius=1, percent=150, threshold=3))


# ─────────────────────────────────────────────────────────────────────────────
# Public API — enhance_document
# ─────────────────────────────────────────────────────────────────────────────

def enhance_document(
    filepath: str,
    report: PreprocessingReport,
    pipeline_id: str,
    output_dir: str,
    trace_fn: Optional[Callable] = None,
) -> str:
    """
    Apply image enhancement to a PDF based on the PreprocessingReport signals.

    Enhancement order: deskew → upscale → denoise → contrast → sharpen
    Rationale for order:
      1. Deskew first so subsequent operations work on straight lines.
      2. Upscale before denoising — denoising a low-res image and then upscaling
         amplifies artifacts after resampling and degrades OCR accuracy.
      3. Denoise, contrast, sharpen are applied in that order (coarse → fine).

    Page cap: PREPROCESS_MAX_ENHANCE_PAGES (default 50). Pages beyond the cap
    are appended to the output PDF at the original render DPI without enhancement.
    This prevents worker timeouts on large scanned documents.

    Args:
        filepath:    Original PDF path
        report:      PreprocessingReport from evaluate_document()
        pipeline_id: Used to name the output file predictably
        output_dir:  Directory to write the enhanced PDF into
        trace_fn:    Optional trace callback

    Returns:
        str: Path to enhanced PDF, or the original filepath if enhancement
             was not needed or could not be applied.

    Output path convention (must match handle_parse_document's lookup):
        output_dir/preprocessed_{pipeline_id}.pdf
    """
    if not report.needs_enhancement:
        return filepath

    if not CV2_AVAILABLE or not PDF2IMAGE_AVAILABLE:
        if trace_fn:
            trace_fn("[PREPROCESS] Enhancement skipped — opencv/pdf2image not installed")
        return filepath

    t_start = time.perf_counter()

    def _t(msg: str):
        logger.info(msg)
        if trace_fn:
            try:
                trace_fn(msg)
            except Exception:
                pass

    from pdf2image import convert_from_path
    from PIL import Image

    page_count = report.page_count
    max_pages = config.PREPROCESS_MAX_ENHANCE_PAGES
    pages_to_enhance = min(page_count, max_pages)

    if page_count > max_pages:
        _t(
            f"[PREPROCESS] WARNING: Document has {page_count} pages. "
            f"Enhancement applied to pages 1–{max_pages} only "
            f"(PREPROCESS_MAX_ENHANCE_PAGES={max_pages}). "
            f"Pages {max_pages + 1}–{page_count} pass through at render DPI without enhancement."
        )

    render_dpi = config.PREPROCESS_TARGET_DPI

    # Determine which enhancements are needed
    needs_upscale = (
        report.dpi_estimate is not None
        and report.dpi_estimate < config.PREPROCESS_DPI_MIN
    )
    enhancements: list[str] = []
    if abs(report.skew_angle) > config.PREPROCESS_SKEW_MAX_DEG:
        enhancements.append("deskew")
    if needs_upscale:
        enhancements.append("upscale")
    if report.noise_score < config.PREPROCESS_NOISE_MIN and config.PREPROCESS_ENABLE_DENOISE:
        enhancements.append("denoise")
    if report.contrast_score < config.PREPROCESS_CONTRAST_MIN:
        enhancements.append("contrast")
    if report.blur_score < config.PREPROCESS_BLUR_MIN and config.PREPROCESS_ENABLE_SHARPEN:
        enhancements.append("sharpen")

    _t(f"[PREPROCESS] Enhancements to apply: {', '.join(enhancements) if enhancements else 'none'}")
    _t(f"[PREPROCESS] Rendering {pages_to_enhance} pages at {render_dpi} DPI for enhancement...")

    # Render pages that will be enhanced
    enhanced_images = convert_from_path(
        filepath,
        first_page=1,
        last_page=pages_to_enhance,
        dpi=render_dpi,
        poppler_path=_get_poppler_path(),
    )

    # Apply enhancement pipeline per page
    # Order: deskew → upscale → denoise → contrast → sharpen
    processed: list = []
    for idx, img in enumerate(enhanced_images):
        try:
            if "deskew" in enhancements:
                img = _apply_deskew(img, report.skew_angle)
            if "upscale" in enhancements:
                src_dpi = int(report.dpi_estimate) if report.dpi_estimate else render_dpi
                img = _apply_upscale(img, source_dpi=src_dpi, target_dpi=render_dpi)
            if "denoise" in enhancements:
                img = _apply_denoise(img)
            if "contrast" in enhancements:
                img = _apply_contrast(img)
            if "sharpen" in enhancements:
                img = _apply_sharpen(img)
            processed.append(img.convert("RGB"))
        except Exception as exc:
            _t(f"[PREPROCESS] WARNING: Enhancement failed on page {idx + 1}: {exc} — using original")
            processed.append(img.convert("RGB"))

    # Append remaining pages (beyond cap) unenhanced
    if page_count > max_pages:
        _t(f"[PREPROCESS] Rendering pages {max_pages + 1}–{page_count} (no enhancement)...")
        remaining = convert_from_path(
            filepath,
            first_page=max_pages + 1,
            last_page=page_count,
            dpi=render_dpi,
            poppler_path=_get_poppler_path(),
        )
        processed.extend([img.convert("RGB") for img in remaining])

    if not processed:
        _t("[PREPROCESS] WARNING: No pages rendered — returning original file")
        return filepath

    # Save all pages as a new PDF
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"preprocessed_{pipeline_id}.pdf")
    first_page = processed[0]
    rest_pages = processed[1:]
    first_page.save(
        output_path,
        format="PDF",
        save_all=True,
        append_images=rest_pages,
        resolution=render_dpi,
    )

    duration_ms = round((time.perf_counter() - t_start) * 1000, 1)
    _t(
        f"[PREPROCESS] Enhancement complete — "
        f"{len(processed)} pages | enhancements: {', '.join(enhancements)} | "
        f"{duration_ms:.0f}ms → {os.path.basename(output_path)}"
    )

    return output_path
