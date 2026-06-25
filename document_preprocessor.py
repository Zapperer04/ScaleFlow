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
import concurrent.futures

logger = logging.getLogger(__name__)

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


# ─────────────────────────────────────────────────────────────────────────────
# Memory Guard
# ─────────────────────────────────────────────────────────────────────────────
def _check_memory_before_render(pages_to_render: int, target_dpi: int):
    estimated_mb = pages_to_render * 30 * (target_dpi / 72) ** 2
    available_mb = psutil.virtual_memory().available / (1024 * 1024)
    if estimated_mb > available_mb * 0.70:
        raise MemoryError(f"Preprocess matrix calculation requires ~{estimated_mb:.0f}MB")


# ─────────────────────────────────────────────────────────────────────────────
# Image Spatial Quality Analysis
# ─────────────────────────────────────────────────────────────────────────────
def analyze_image_spatial_quality(image_np: np.ndarray) -> Tuple[float, float, float]:
    gray = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY) if len(image_np.shape) == 3 else image_np
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    std_dev = np.std(gray)
    h, w = gray.shape
    edges = cv2.Canny(gray, 50, 150)
    edge_density = (np.sum(edges > 0) / (h * w)) * 100.0
    return float(laplacian_var), float(std_dev), float(edge_density)


# ─────────────────────────────────────────────────────────────────────────────
# Text Coherence Scoring
# Checks whether extracted PDF text is actually readable, not garbage.
# Returns score 0–100. Low score = corrupt font mapping or scanned image PDF.
# ─────────────────────────────────────────────────────────────────────────────
def _score_text_coherence(text: str) -> float:
    if not text or len(text.strip()) < 20:
        return 0.0

    import re
    lines = [l for l in text.splitlines() if l.strip()]
    tokens = re.findall(r"[a-zA-Z]{2,}", text)
    total_nonws = len(re.sub(r"\s", "", text)) or 1

    # Word length score — real words average 3–9 chars
    if tokens:
        avg_len = sum(len(t) for t in tokens) / len(tokens)
        word_length_score = max(0.0, 100.0 - abs(avg_len - 6.0) * 15.0)
        single_ratio = sum(1 for t in tokens if len(t) == 1) / len(tokens)
        word_length_score *= max(0.0, 1.0 - single_ratio * 2.0)
    else:
        word_length_score = 0.0

    # Alpha density — real text is 55–85% alphabetic
    alpha_chars = sum(len(t) for t in tokens)
    alpha_ratio = alpha_chars / total_nonws
    whitespace_score = min(100.0, max(0.0, (alpha_ratio - 0.35) / 0.50 * 100.0))

    # Line coherence — ratio of lines with ≥2 real words
    if lines:
        coherent_lines = sum(1 for l in lines if len(re.findall(r"[a-zA-Z]{2,}", l)) >= 2)
        line_coherence_score = (coherent_lines / len(lines)) * 100.0
    else:
        line_coherence_score = 0.0

    score = (
        word_length_score  * 40.0
        + whitespace_score * 30.0
        + line_coherence_score * 30.0
    ) / 100.0

    return round(min(100.0, max(0.0, score)), 1)


# ─────────────────────────────────────────────────────────────────────────────
# Preprocessing Report — all fields the worker pipeline reads
# ─────────────────────────────────────────────────────────────────────────────
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


# ─────────────────────────────────────────────────────────────────────────────
# Document Preprocessor
# ─────────────────────────────────────────────────────────────────────────────
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

        # ── Non-PDF / plain text fast path ───────────────────────────────────
        ext = os.path.splitext(self.filename)[-1].lower()
        if ext == ".txt":
            _t("[PREPROCESS] Plain text file — direct parse")
            return report
        if ext not in [".pdf"]:
            _t(f"[PREPROCESS] Unsupported format {ext} — routing to VLM")
            report.document_type = "SCANNED"
            report.routing_action = "VLM_ENHANCE_ROUTE"
            report.parse_method_hint = "vlm_local_api"
            report.routing_confidence = 0.5
            return report

        # ── Phase 1: Structural guard ─────────────────────────────────────────
        try:
            with open(self.file_path, "rb") as f:
                reader = pypdf.PdfReader(f)
                if reader.is_encrypted:
                    if not reader.decrypt(""):
                        report.is_encrypted = True
                        report.routing_action = "VLM_ENHANCE_ROUTE"
                        report.parse_method_hint = "vlm_local_api"
                        report.document_type = "SCANNED"
                        _t("[PREPROCESS] PDF is password-encrypted — routing to VLM")
                        return report
                page_count = len(reader.pages)
                if page_count == 0:
                    report.is_corrupted = True
                    report.warnings.append("PDF has zero pages")
                    _t("[PREPROCESS] PDF has zero pages")
                    return report

                # ── Phase 2: Text extraction probe ───────────────────────────
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
            _t(f"[PREPROCESS] Structural read failed: {e} — routing to VLM")
            report.is_corrupted = True
            report.document_type = "SCANNED"
            report.routing_action = "VLM_ENHANCE_ROUTE"
            report.parse_method_hint = "vlm_local_api"
            report.needs_enhancement = True
            report.routing_confidence = 0.5
            return report

        # ── Phase 3: Image quality assessment ────────────────────────────────
        blur_accum, contrast_accum, edge_accum = [], [], []
        try:
            from pdf2image import convert_from_path
            _check_memory_before_render(sample_limit, 150)
            images = convert_from_path(
                self.file_path, first_page=1, last_page=sample_limit, dpi=150
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
            _t(f"[PREPROCESS] Image quality assessment failed: {e} — using fallback values")
            report.average_blur_score     = 1000.0
            report.average_contrast_score = 50.0

        # ── Phase 4: Coherence check on extracted text ────────────────────────
        # Even if pypdf extracted chars, they may be garbage (corrupt font maps,
        # scanned-image PDFs with embedded dummy text, etc.)
        text_coherence_score = 0.0
        if sampled_texts:
            combined = "\n".join(sampled_texts)
            text_coherence_score = _score_text_coherence(combined)
            _t(f"[PREPROCESS] Text coherence score: {text_coherence_score:.1f}/100")

        # ── Phase 5: Routing decision ─────────────────────────────────────────
        # DIGITAL: enough chars AND coherent text AND image quality is acceptable
        # Everything else → VLM (handles scanned, handwritten, mixed, corrupt fonts)
        is_text_sufficient   = report.extractable_text_ratio >= 30.0
        is_text_coherent     = text_coherence_score >= getattr(config, "MIN_QUALITY_CONFIDENCE", 50.0)
        is_image_sharp       = report.average_blur_score >= getattr(config, "PREPROCESS_BLUR_MIN", 300.0)
        has_few_empty_pages  = empty_pages <= (sample_limit * 0.4)

        if is_text_sufficient and is_text_coherent and has_few_empty_pages:
            report.document_type    = "DIGITAL"
            report.routing_action   = "DIRECT_PARSE"
            report.parse_method_hint = "pypdf"
            report.overall_quality_score = text_coherence_score
            report.overall_quality       = text_coherence_score
            report.routing_confidence    = 1.0
            _t(f"[PREPROCESS] Route: DIGITAL → pypdf (coherence={text_coherence_score:.1f})")
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
            if not is_text_coherent:
                reasons.append(f"incoherent text (score={text_coherence_score:.1f})")
            if not has_few_empty_pages:
                reasons.append(f"too many empty pages ({empty_pages}/{sample_limit})")
            _t(f"[PREPROCESS] Route: VLM — reasons: {', '.join(reasons)}")

        report.timings["total_preprocess_secs"] = round(time.perf_counter() - t_start, 3)
        _t(f"[PREPROCESS] Done in {report.timings['total_preprocess_secs']}s")
        return report


# ─────────────────────────────────────────────────────────────────────────────
# Public API — called by worker
# ─────────────────────────────────────────────────────────────────────────────
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


# ─────────────────────────────────────────────────────────────────────────────
# VLM Transcription — Gemini 1.5 Flash, concurrent page batches with backoff
# Called by handle_parse_document when parse_method_hint == "vlm_local_api"
# ─────────────────────────────────────────────────────────────────────────────
def execute_vlm_extraction_step(file_path: str, pipeline_id: int, trace_fn: Optional[Callable] = None) -> str:
    def _t(msg: str):
        logger.info(msg)
        if trace_fn:
            try:
                trace_fn(msg)
            except Exception:
                pass

    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY environment variable missing.")

    gemini_endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-1.5-flash:generateContent?key={gemini_api_key}"
    )

    try:
        from pdf2image import convert_from_path
        images = convert_from_path(file_path, dpi=150)
        _t(f"[VLM] Transcribing {len(images)} page(s) via Gemini 1.5 Flash")
        
        results_map = {}

        def transcribe_page(page_idx, img):
            max_retries = 5
            backoff = 2
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
                    elif res.status_code == 429:
                        sleep_time = backoff ** attempt
                        _t(f"[VLM] Page {page_idx + 1} rate limited (429). Retrying in {sleep_time}s... (Attempt {attempt+1}/{max_retries})")
                        time.sleep(sleep_time)
                        continue
                    else:
                        _t(f"[VLM] Page {page_idx + 1} failed: HTTP {res.status_code} — {res.text[:200]}")
                        return page_idx, f"[PAGE {page_idx + 1} TRANSCRIPTION FAILED]"
                except Exception as e:
                    if attempt < max_retries - 1:
                        sleep_time = backoff ** attempt
                        _t(f"[VLM] Page {page_idx + 1} error: {e}. Retrying in {sleep_time}s... (Attempt {attempt+1}/{max_retries})")
                        time.sleep(sleep_time)
                        continue
                    _t(f"[VLM] Page {page_idx + 1} error: {e}")
                    return page_idx, f"[PAGE {page_idx + 1} ERROR: {e}]"
            
            return page_idx, f"[PAGE {page_idx + 1} RETRIES EXHAUSTED]"

        max_workers = int(os.getenv("VLM_CONCURRENCY", "4"))
        _t(f"[VLM] Starting parallel transcription with {max_workers} threads")

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(transcribe_page, idx, img) for idx, img in enumerate(images)]
            for future in concurrent.futures.as_completed(futures):
                try:
                    idx, text = future.result()
                    results_map[idx] = text
                except Exception as e:
                    _t(f"[VLM] Thread execution error: {e}")

        consolidated = [results_map.get(idx, f"[PAGE {idx + 1} MISSING]") for idx in range(len(images))]
        result = "\n\n<--- PAGE_BREAK --->\n\n".join(consolidated)
        _t(f"[VLM] Transcription complete — {len(result)} total chars")
        return result

    except Exception as e:
        raise RuntimeError(f"VLM transcription failed: {e}")