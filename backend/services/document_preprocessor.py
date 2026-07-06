import os
import json
import base64
import logging
import requests
import pypdf
import cv2
import numpy as np
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Any, Tuple
import psutil
import time
import threading
import concurrent.futures

logger = logging.getLogger(__name__)

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


# -----
# Gemini shared rate limiter
# Free tier is ~15 RPM. With N threads hammering simultaneously each thread's
# backoff is blind to the others, causing repeated 429/503 storms.
# Serialising the actual network call to 1 request / GEMINI_MIN_INTERVAL_SECONDS
# eliminates that while still letting threads do image encoding in parallel.
# -----
_gemini_rate_lock = threading.Lock()
_gemini_last_call_time = [0.0]
GEMINI_MIN_INTERVAL_SECONDS = float(os.getenv("GEMINI_MIN_INTERVAL_SECONDS", "6.0"))

def _gemini_throttle():
    """Blocks the calling thread until it's safe to make the next Gemini call."""
    with _gemini_rate_lock:
        elapsed = time.time() - _gemini_last_call_time[0]
        wait = GEMINI_MIN_INTERVAL_SECONDS - elapsed
        if wait > 0:
            time.sleep(wait)
        _gemini_last_call_time[0] = time.time()


# -----
# Memory Guard
# -----
def _check_memory_before_render(pages_to_render: int, target_dpi: int):
    estimated_mb = pages_to_render * 30 * (target_dpi / 72) ** 2
    available_mb = psutil.virtual_memory().available / (1024 * 1024)
    if estimated_mb > available_mb * 0.70:
        raise MemoryError(f"Preprocess matrix calculation requires ~{estimated_mb:.0f}MB")



# -----
# Image Spatial Quality Analysis
# -----
def analyze_image_spatial_quality(image_np: np.ndarray) -> Tuple[float, float, float]:
    """Returns (laplacian_variance, std_dev, edge_density_pct) for a rendered page image."""
    gray = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY) if len(image_np.shape) == 3 else image_np
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    std_dev = np.std(gray)
    h, w = gray.shape
    edges = cv2.Canny(gray, 50, 150)
    edge_density = (np.sum(edges > 0) / (h * w)) * 100.0
    return float(laplacian_var), float(std_dev), float(edge_density)


# -----
# Text Coherence Scoring
# -----


def _score_text_coherence(text: str) -> float:
    """
    Score 0-100. High = clean readable text (digital PDF). Low = garbled OCR noise.

    Design principle: **positive-first**.
    We start at 0 and AWARD points for signals that confirm real text,
    then apply a final penalty multiplier for confirmed OCR artifacts.
    This avoids over-penalisation of technical/structured content
    (code, tables, lists, numbers) that looks "abnormal" to prose-only metrics.
    """
    if not text or len(text.strip()) < 20:
        return 0.0

    import re
    lines = [l for l in text.splitlines() if l.strip()]
    tokens = re.findall(r"[a-zA-Z]{2,}", text)
    total_nonws = len(re.sub(r"\s", "", text)) or 1

    if not tokens:
        return 0.0

    score = 0.0

    # Signal 1: Word character density (25 pts)
    # Real text is at least 40% alphabetic. OCR garbage has symbol runs.
    alpha_chars = sum(len(t) for t in tokens)
    alpha_ratio = alpha_chars / total_nonws
    if alpha_ratio >= 0.55:
        score += 25.0
    elif alpha_ratio >= 0.40:
        score += 15.0
    elif alpha_ratio >= 0.25:
        score += 5.0

    # Signal 2: Avg word length plausibility (25 pts)
    # Real words average 3-10 chars. OCR noise hits extremes.
    avg_len = sum(len(t) for t in tokens) / len(tokens)
    if 3.0 <= avg_len <= 10.0:
        score += 25.0
    elif 2.0 <= avg_len <= 12.0:
        score += 15.0
    elif avg_len <= 15.0:
        score += 5.0

    # Signal 3: Line density (25 pts)
    # Lines with >=2 alpha tokens = content lines. Tables and lists pass this.
    if lines:
        content_lines = sum(1 for l in lines if len(re.findall(r"[a-zA-Z]{2,}", l)) >= 2)
        content_ratio = content_lines / len(lines)
        if content_ratio >= 0.50:
            score += 25.0
        elif content_ratio >= 0.30:
            score += 15.0
        elif content_ratio >= 0.15:
            score += 5.0

    # Signal 4: Minimum text volume (10 pts)
    # Very short extracted text is suspicious ----- scanned PDFs yield near-empty results.
    if len(tokens) >= 100:
        score += 10.0
    elif len(tokens) >= 30:
        score += 5.0

    # Penalty multiplier: confirmed OCR artifacts only
    # We only deduct here for things that ONLY appear in garbled OCR output.
    penalty = 1.0

    # Replacement character (U+FFFD) ----- absolute sign of corrupt encoding
    repl_ratio = text.count('\ufffd') / len(text)
    if repl_ratio > 0.02:
        penalty *= 0.1
    elif repl_ratio > 0.01:
        penalty *= 0.3

    # Words with alpha-digit mixtures: "l0ok", "C0mputer", "f1rst"
    # Only penalise above 10% ----- version strings/code tokens are legitimate
    ocr_digit_words = sum(1 for t in tokens if re.search(r'[a-zA-Z]\d|\d[a-zA-Z]', t))
    ocr_digit_ratio = ocr_digit_words / len(tokens)
    if ocr_digit_ratio > 0.15:
        penalty *= 0.4
    elif ocr_digit_ratio > 0.10:
        penalty *= 0.7

    # Excessive double-spaces ----- strong OCR spacing artifact signal
    if lines:
        dbl_spaces_per_line = len(re.findall(r'  +', text)) / len(lines)
        if dbl_spaces_per_line > 6:
            penalty *= 0.3
        elif dbl_spaces_per_line > 3:
            penalty *= 0.6

    # All-caps runs (OCR artifact)
    all_caps_words = sum(1 for t in tokens if t.isupper() and len(t) > 2)
    if all_caps_words > len(tokens) * 0.20:
        penalty *= 0.5

    # Short/fused words (OCR artifact)
    fused_short = sum(1 for t in tokens if len(t) < 4)
    if fused_short / len(tokens) > 0.25:
        penalty *= 0.5

    return round(min(100.0, max(0.0, score * penalty)), 1)


# Preprocessing Report -- all fields the worker pipeline reads
@dataclass
class PreprocessingReport:
    # Routing
    document_type: str = "DIGITAL"
    routing_action: str = "DIRECT_PARSE"
    parse_method_hint: str = "pypdf"
    # Image quality metrics
    extractable_text_ratio: float = 0.0
    average_blur_score: float = 0.0
    average_contrast_score: float = 0.0
    average_edge_density: float = 0.0
    handwritten_confidence: float = 0.0
    # Enhancement
    needs_enhancement: bool = False
    used_enhancement: bool = False
    enhancement_flags: dict = field(default_factory=dict)
    timings: dict = field(default_factory=dict)
    # Worker pipeline compatibility fields
    hard_reject: bool = False
    reject_reason: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    overall_quality_score: float = 100.0
    overall_quality: float = 100.0
    routing_confidence: float = 1.0
    enhanced_pages_path: Optional[str] = None
    quality_scores: dict = field(default_factory=lambda: {
        "blur": 0.0, "contrast": 0.0, "noise": 0.0, "skew_angle": 0.0
    })
    is_encrypted: bool = False
    is_corrupted: bool = False


# -----
# Document Preprocessor
# -----
class DocumentPreprocessor:
    def __init__(self, file_path: str):
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        self.file_path = file_path
        self.filename = os.path.basename(file_path)

    def generate_routing_report(self, trace_fn: Optional[Callable] = None) -> PreprocessingReport:
        def _t(msg: str):
            logger.info(msg)
            if trace_fn:
                try:
                    trace_fn(msg)
                except Exception:
                    pass

        t_start = time.perf_counter()
        report = PreprocessingReport()

        # ----- Non-PDF / plain text fast path -----
        ext = os.path.splitext(self.filename)[-1].lower()
        if ext == ".txt":
            _t("[PREPROCESS] Plain text file ??? direct parse")
            return report
        if ext not in [".pdf"]:
            _t(f"[PREPROCESS] Unsupported format {ext} ??? routing to VLM")
            report.document_type = "SCANNED"
            report.routing_action = "VLM_ENHANCE_ROUTE"
            report.parse_method_hint = "vlm_local_api"
            report.routing_confidence = 0.5
            return report

        # ----- Phase 1: Structural guard -----
        try:
            with open(self.file_path, "rb") as f:
                reader = pypdf.PdfReader(f)
                if reader.is_encrypted:
                    if not reader.decrypt(""):
                        report.is_encrypted = True
                        report.routing_action = "VLM_ENHANCE_ROUTE"
                        report.parse_method_hint = "vlm_local_api"
                        report.document_type = "SCANNED"
                        _t("[PREPROCESS] PDF is password-encrypted ??? routing to VLM")
                        return report
                page_count = len(reader.pages)
                if page_count == 0:
                    report.is_corrupted = True
                    report.warnings.append("PDF has zero pages")
                    _t("[PREPROCESS] PDF has zero pages")
                    return report

                # ----- Phase 2: Text extraction probe -----
                sample_limit = min(page_count, 5)
                text_chars = 0
                empty_pages = 0
                sampled_texts = []

                for i in range(sample_limit):
                    try:
                        text = (reader.pages[i].extract_text() or "").strip()
                        text_chars += len(text)
                        if text:
                            sampled_texts.append(text)
                        if len(text) < 20:
                            empty_pages += 1
                    except Exception:
                        empty_pages += 1

                report.extractable_text_ratio = text_chars / max(sample_limit, 1)
                _t(f"[PREPROCESS] Text probe: {text_chars} chars, {empty_pages} empty pages, ratio={report.extractable_text_ratio:.1f}")

        except Exception as e:
            _t(f"[PREPROCESS] Structural read failed: {e} ??? routing to VLM")
            report.is_corrupted = True
            report.document_type = "SCANNED"
            report.routing_action = "VLM_ENHANCE_ROUTE"
            report.parse_method_hint = "vlm_local_api"
            report.needs_enhancement = True
            report.routing_confidence = 0.5
            return report

        # ----- Phase 3: Image quality assessment -----
        blur_accum, contrast_accum, edge_accum = [], [], []
        try:
            from pdf2image import convert_from_path
            _check_memory_before_render(sample_limit, 150)
            poppler_path = getattr(config, "PREPROCESS_POPPLER_PATH", None) or os.getenv("PREPROCESS_POPPLER_PATH") or None
            images = convert_from_path(
                self.file_path, first_page=1, last_page=sample_limit, dpi=150,
                poppler_path=poppler_path
            )
            for img in images:
                b, c, e = analyze_image_spatial_quality(np.array(img))
                blur_accum.append(b)
                contrast_accum.append(c)
                edge_accum.append(e)
            if blur_accum:
                report.average_blur_score    = sum(blur_accum)    / len(blur_accum)
                report.average_contrast_score = sum(contrast_accum) / len(contrast_accum)
                report.average_edge_density   = sum(edge_accum)    / len(edge_accum)
                report.quality_scores = {
                    "blur":       report.average_blur_score,
                    "contrast":   report.average_contrast_score,
                    "noise":      0.0,
                    "skew_angle": 0.0
                }
                _t(
                    f"[PREPROCESS] Image quality: blur={report.average_blur_score:.1f}, "
                    f"contrast={report.average_contrast_score:.1f}, "
                    f"edge_density={report.average_edge_density:.2f}"
                )
        except Exception as e:
            _t(f"[PREPROCESS] Image quality assessment failed: {e} ??? using fallback values")
            report.average_blur_score     = 1000.0
            report.average_contrast_score = 50.0

        # ----- Phase 4: Coherence check on extracted text -----
        # Even if pypdf extracted chars, they may be garbage (corrupt font maps,
        # scanned-image PDFs with embedded dummy text, etc.)
        text_coherence_score = 0.0
        if sampled_texts:
            combined = "\n".join(sampled_texts)
            text_coherence_score = _score_text_coherence(combined)
            _t(f"[PREPROCESS] Text coherence score: {text_coherence_score:.1f}/100")

        # ----- Phase 5: Routing decision -----
        # PRIMARY gate: extractable_text_ratio ----- the most reliable signal.
        # If pypdf pulls substantial text, it's a digital PDF regardless of prose quality.
        # SECONDARY gate: coherence score as a soft filter against corrupt font maps
        # that yield high char counts but unreadable garbage.
        #
        # Thresholds (tuned empirically):
        #   extractable_text_ratio >= 150 chars/page  ----- clearly digital
        #   extractable_text_ratio >= 30 chars/page   ----- possibly digital, check coherence
        #   text_coherence_score   >= 20              ----- not OCR garbage (wide gate)
        #   empty_pages            <= 40%             ----- not a pure image PDF
        is_clearly_digital   = report.extractable_text_ratio >= 150.0  # ~1 sentence/page minimum
        is_maybe_digital     = report.extractable_text_ratio >= 30.0
        is_text_sufficient   = report.extractable_text_ratio >= 30.0
        is_coherent_enough   = text_coherence_score >= 20.0  # Soft gate ??? only filters pure garbage
        has_few_empty_pages  = empty_pages <= (sample_limit * 0.4)

        # Route DIGITAL if:
        #   (clearly digital text volume) OR (some text AND coherent) AND not mostly empty
        if (is_clearly_digital or (is_text_sufficient and is_coherent_enough)) and has_few_empty_pages:
            report.document_type    = "DIGITAL"
            report.routing_action   = "DIRECT_PARSE"
            report.parse_method_hint = "pypdf"
            report.overall_quality_score = text_coherence_score
            report.overall_quality       = text_coherence_score
            report.routing_confidence    = 1.0
            _t(f"[PREPROCESS] Route: DIGITAL ??? pypdf (ratio={report.extractable_text_ratio:.0f} chars/pg, coherence={text_coherence_score:.1f})")

        else:
            report.document_type    = "SCANNED"
            report.routing_action = "VLM_ENHANCE_ROUTE"
            report.parse_method_hint = "vlm_local_api"
            report.needs_enhancement = True
            report.overall_quality_score = text_coherence_score
            report.overall_quality       = text_coherence_score
            report.routing_confidence    = 0.8
            reasons = []
            if not is_text_sufficient:
                reasons.append(f"low text ratio ({report.extractable_text_ratio:.1f} chars/page)")
            if not is_coherent_enough:
                reasons.append(f"incoherent text (score={text_coherence_score:.1f})")
            if not has_few_empty_pages:
                reasons.append(f"too many empty pages ({empty_pages}/{sample_limit})")
            _t(f"[PREPROCESS] Route: VLM ??? reasons: {', '.join(reasons)}")

        report.timings["total_preprocess_secs"] = round(time.perf_counter() - t_start, 3)
        _t(f"[PREPROCESS] Done in {report.timings['total_preprocess_secs']}s")
        return report


# -----
# Public API ----- called by worker
# -----
def evaluate_document(file_path: str, trace_fn: Optional[Callable] = None, *args, **kwargs) -> PreprocessingReport:
    """Entry point called by handle_preprocess_document in the worker."""
    return DocumentPreprocessor(file_path).generate_routing_report(trace_fn=trace_fn)


def structural_guard(*args, **kwargs):
    """Backward-compatibility stub."""
    return None


def run_enhancement_pipeline(
    filepath: str,
    report: PreprocessingReport,
    pipeline_id: str,
    output_dir: str,
    page_count: int = 1,
) -> Optional[str]:
    """
    Backward-compatibility stub.
    Enhancement for non-digital docs is handled by VLM transcription,
    not by image processing. Returns None so the worker skips this path.
    """
    return None


# -----
# VLM Transcription ----- Gemini 1.5 Flash, concurrent page batches with backoff
# Called by handle_parse_document when parse_method_hint == "vlm_local_api"
# -----
def execute_vlm_extraction_step(file_path: str, pipeline_id: int, trace_fn: Optional[Callable] = None) -> str:
    def _t(msg: str):
        logger.info(msg)
        if trace_fn:
            try:
                trace_fn(msg)
            except Exception:
                pass

    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key or "placeholder" in gemini_api_key.lower():
        raise ValueError("GEMINI_API_KEY environment variable missing or is a placeholder.")

    gemini_endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.5-flash:generateContent?key={gemini_api_key}"
    )

    try:
        from pdf2image import convert_from_path
        poppler_path = getattr(config, "PREPROCESS_POPPLER_PATH", None) or os.getenv("PREPROCESS_POPPLER_PATH") or None
        images = convert_from_path(file_path, dpi=150, poppler_path=poppler_path)
        _t(f"[VLM] Transcribing {len(images)} page(s) via Gemini 1.5 Flash")
        
        results_map = {}

        def transcribe_page(page_idx, img):
            import random
            max_retries = 5
            base_delay = 5.0  # seconds ??? safe floor for gemini-2.5-flash free tier
            for attempt in range(max_retries):
                try:
                    _, buffer = cv2.imencode(
                        ".png", cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                    )
                    base64_image = base64.b64encode(buffer).decode("utf-8")
                    payload = {
                        "contents": [{
                            "parts": [
                                {
                                    "text": (
                                        "You are a document transcription engine. "
                                        "Extract ALL text from this page exactly as it appears. "
                                        "Preserve structure, headings, tables, lists, and equations. "
                                        "Output clean markdown. Do not summarize or skip any content."
                                    )
                                },
                                {
                                    "inlineData": {
                                        "mimeType": "image/png",
                                        "data": base64_image
                                    }
                                }
                            ]
                        }]
                    }
                    # Throttle BEFORE the network call so all threads share
                    # one global rate limit instead of racing the free-tier RPM cap.
                    _gemini_throttle()
                    res = requests.post(
                        gemini_endpoint,
                        headers={"Content-Type": "application/json"},
                        json=payload,
                        timeout=60
                    )
                    if res.status_code == 200:
                        page_text = res.json()["candidates"][0]["content"]["parts"][0]["text"]
                        _t(f"[VLM] Page {page_idx + 1}/{len(images)} transcribed ({len(page_text)} chars)")
                        return page_idx, page_text
                    elif res.status_code in (429, 503):
                        # Log the EXACT Gemini error so we can diagnose quota vs rate limit
                        try:
                            err_body = res.json()
                        except Exception:
                            err_body = res.text[:500]
                        sleep_time = base_delay * (2 ** attempt) + random.uniform(0, 3)
                        _t(
                            f"[VLM] Page {page_idx + 1} got HTTP {res.status_code} "
                            f"(Attempt {attempt + 1}/{max_retries}). "
                            f"Gemini error: {err_body}. "
                            f"Retrying in {sleep_time:.1f}s..."
                        )
                        time.sleep(sleep_time)
                        continue
                    elif res.status_code in (400, 401, 403):
                        raise RuntimeError(f"API key invalid or unauthorized: HTTP {res.status_code} - {res.text}")
                    else:
                        _t(f"[VLM] Page {page_idx + 1} failed: HTTP {res.status_code} ??? {res.text[:500]}")
                        raise RuntimeError(f"VLM page transcription failed with HTTP {res.status_code}: {res.text[:300]}")
                except Exception as e:
                    if isinstance(e, RuntimeError) and "API key invalid" in str(e):
                        raise
                    if attempt < max_retries - 1:
                        sleep_time = base_delay * (2 ** attempt) + random.uniform(0, 3)
                        _t(
                            f"[VLM] Page {page_idx + 1} exception: {type(e).__name__}: {e}. "
                            f"Retrying in {sleep_time:.1f}s... (Attempt {attempt + 1}/{max_retries})"
                        )
                        time.sleep(sleep_time)
                        continue
                    _t(f"[VLM] Page {page_idx + 1} FINAL ERROR after {max_retries} attempts: {type(e).__name__}: {e}")
                    return page_idx, f"[PAGE {page_idx + 1} ERROR: {type(e).__name__}: {e}]"

            return page_idx, f"[PAGE {page_idx + 1} RETRIES EXHAUSTED after {max_retries} attempts]"

        # Concurrency only helps with image encoding now; network calls are
        # globally throttled. Default lowered to 2 to reduce memory pressure.
        max_workers = int(os.getenv("VLM_CONCURRENCY", "2"))
        _t(f"[VLM] Starting transcription with {max_workers} thread(s), throttled to 1 req/{GEMINI_MIN_INTERVAL_SECONDS}s globally")

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(transcribe_page, idx, img) for idx, img in enumerate(images)]
            for future in concurrent.futures.as_completed(futures):
                try:
                    idx, text = future.result()
                    results_map[idx] = text
                except Exception as e:
                    _t(f"[VLM] Thread execution error: {e}")

        consolidated = [results_map.get(idx, f"[PAGE {idx + 1} MISSING]") for idx in range(len(images))]

        # Detect and quarantine failed pages ----- never index sentinel strings
        FAILURE_MARKERS = ("RETRIES EXHAUSTED", "TRANSCRIPTION FAILED", "MISSING]", "ERROR:")
        failed_count = sum(1 for p in consolidated if any(m in p for m in FAILURE_MARKERS))
        if failed_count:
            failure_rate = failed_count / len(consolidated)
            _t(f"[VLM] WARNING: {failed_count}/{len(consolidated)} pages failed ({failure_rate:.0%})")
            if failure_rate > 0.20:
                raise RuntimeError(
                    f"VLM transcription degraded: {failed_count}/{len(consolidated)} pages failed "
                    f"({failure_rate:.0%} > 20% threshold). Aborting to prevent garbage indexing."
                )
        # Drop individual failed pages so they never reach the chunker
        consolidated = [p for p in consolidated if not any(m in p for m in FAILURE_MARKERS)]

        result = "\n\n<--- PAGE_BREAK --->\n\n".join(consolidated)
        _t(f"[VLM] Transcription complete ??? {len(result)} total chars ({len(consolidated)}/{len(images)} pages OK)")
        return result

    except Exception as e:
        raise RuntimeError(f"VLM transcription failed: {e}")
