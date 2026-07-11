import os
import json
import base64
import logging
import requests
import pypdf
import cv2
import numpy as np
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Any, Tuple, Dict
import psutil
import time
import threading
import concurrent.futures

# Import the centralized rate manager
from services.gemini_rate_manager import GeminiRateManager, RateLimitPauseRequired

logger = logging.getLogger(__name__)

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# pdf2image import moved to top for reuse
from pdf2image import convert_from_path


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
# ─────────────────────────────────────────────────────────────────────────────
def _score_text_coherence(text: str) -> float:
    if not text or len(text.strip()) < 20:
        return 0.0

    import re
    lines = [l for l in text.splitlines() if l.strip()]
    tokens = re.findall(r"[a-zA-Z]{2,}", text)
    total_nonws = len(re.sub(r"\s", "", text)) or 1

    if tokens:
        avg_len = sum(len(t) for t in tokens) / len(tokens)
        word_length_score = max(0.0, 100.0 - abs(avg_len - 6.0) * 15.0)
        single_ratio = sum(1 for t in tokens if len(t) == 1) / len(tokens)
        word_length_score *= max(0.0, 1.0 - single_ratio * 2.0)
    else:
        word_length_score = 0.0

    alpha_chars = sum(len(t) for t in tokens)
    alpha_ratio = alpha_chars / total_nonws
    whitespace_score = min(100.0, max(0.0, (alpha_ratio - 0.35) / 0.50 * 100.0))

    if lines:
        coherent_lines = sum(1 for l in lines if len(re.findall(r"[a-zA-Z]{2,}", l)) >= 2)
        line_coherence_score = (coherent_lines / len(lines)) * 100.0
    else:
        line_coherence_score = 0.0

    score = (word_length_score * 40.0 + whitespace_score * 30.0 + line_coherence_score * 30.0) / 100.0
    return round(min(100.0, max(0.0, score)), 1)


# ─────────────────────────────────────────────────────────────────────────────
# Preprocessing Report
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class PreprocessingReport:
    document_type: str = "DIGITAL"
    routing_action: str = "DIRECT_PARSE"
    parse_method_hint: str = "pypdf"
    extractable_text_ratio: float = 0.0
    average_blur_score: float = 0.0
    average_contrast_score: float = 0.0
    average_edge_density: float = 0.0
    handwritten_confidence: float = 0.0
    needs_enhancement: bool = False
    used_enhancement: bool = False
    enhancement_flags: dict = field(default_factory=dict)
    timings: dict = field(default_factory=dict)
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
# Document Preprocessor (Routing & Classification only)
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

        blur_accum, contrast_accum, edge_accum = [], [], []
        try:
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

        text_coherence_score = 0.0
        if sampled_texts:
            combined = "\n".join(sampled_texts)
            text_coherence_score = _score_text_coherence(combined)
            _t(f"[PREPROCESS] Text coherence score: {text_coherence_score:.1f}/100")

        is_text_sufficient   = report.extractable_text_ratio >= 30.0
        is_text_coherent     = text_coherence_score >= getattr(config, "MIN_QUALITY_CONFIDENCE", 50.0)
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
    return DocumentPreprocessor(file_path).generate_routing_report(trace_fn=trace_fn)


def structural_guard(*args, **kwargs):
    return None


def run_enhancement_pipeline(
    filepath: str,
    report: PreprocessingReport,
    pipeline_id: str,
    output_dir: str,
    page_count: int = 1,
) -> Optional[str]:
    return None


# ─────────────────────────────────────────────────────────────────────────────
# VLM Page Transcription (Stateless, uses GeminiRateManager)
# ─────────────────────────────────────────────────────────────────────────────
def _transcribe_single_page(
    page_idx: int,          # 0-indexed
    image: np.ndarray,
    gemini_endpoint: str,
    rate_mgr: GeminiRateManager,
    trace_fn: Optional[Callable] = None,
    max_retries: int = 3,
) -> Tuple[int, Optional[str]]:
    """
    Transcribe a single page using Gemini. Assumes the rate manager has already
    been checked (get_decision called) and a slot acquired.
    Returns (page_idx, text) or (page_idx, None) on failure.
    """
    def _t(msg: str):
        if trace_fn:
            try:
                trace_fn(msg)
            except Exception:
                pass

    last_error = None
    for attempt in range(max_retries):
        try:
            # Encode image
            _, buffer = cv2.imencode(".png", cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR))
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

            # Make the request
            res = requests.post(
                gemini_endpoint,
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=60
            )

            if res.status_code == 200:
                page_text = res.json()["candidates"][0]["content"]["parts"][0]["text"]
                _t(f"[VLM] Page {page_idx+1} transcribed ({len(page_text)} chars)")
                rate_mgr.register_success()
                return page_idx, page_text
            elif res.status_code in (429, 503) or "quota" in res.text.lower() or "rate limit" in res.text.lower():
                # Rate limit – register 429 and raise pause exception
                retry_after = 60.0
                try:
                    retry_after = float(res.headers.get("Retry-After", 60.0))
                except:
                    pass
                rate_mgr.register_429(retry_after_header=res.headers.get("Retry-After"))
                raise RateLimitPauseRequired(
                    resume_at=time.time() + retry_after,
                    reason="rate_limit",
                    retry_after=retry_after
                )
            else:
                # Other HTTP error – retry if transient
                if res.status_code in (500, 502, 504):
                    # Server error – retry
                    sleep_time = 2 ** attempt
                    _t(f"[VLM] Page {page_idx+1} got HTTP {res.status_code}. Retrying in {sleep_time}s... (Attempt {attempt+1}/{max_retries})")
                    time.sleep(sleep_time)
                    continue
                else:
                    _t(f"[VLM] Page {page_idx+1} failed: HTTP {res.status_code} — {res.text[:200]}")
                    return page_idx, None

        except RateLimitPauseRequired:
            raise  # re-raise to outer handler
        except requests.exceptions.Timeout:
            last_error = "timeout"
            sleep_time = 2 ** attempt
            _t(f"[VLM] Page {page_idx+1} timeout. Retrying in {sleep_time}s... (Attempt {attempt+1}/{max_retries})")
            time.sleep(sleep_time)
            continue
        except requests.exceptions.ConnectionError:
            last_error = "connection_error"
            sleep_time = 2 ** attempt
            _t(f"[VLM] Page {page_idx+1} connection error. Retrying in {sleep_time}s... (Attempt {attempt+1}/{max_retries})")
            time.sleep(sleep_time)
            continue
        except Exception as e:
            _t(f"[VLM] Page {page_idx+1} error: {e}")
            return page_idx, None

    _t(f"[VLM] Page {page_idx+1} failed after {max_retries} attempts: {last_error}")
    return page_idx, None


def transcribe_pages(
    file_path: str,
    page_numbers: List[int],   # 1-indexed page numbers to transcribe
    trace_fn: Optional[Callable] = None,
) -> Dict[int, str]:
    """
    Transcribe the specified pages of a PDF using Gemini.
    Returns a dict mapping 1-indexed page number to transcribed text.
    Pages that fail are omitted from the dict.
    Raises RateLimitPauseRequired if a transient rate limit is encountered.
    This is the core stateless transcription function.
    """
    if not page_numbers:
        return {}

    def _t(msg: str):
        if trace_fn:
            try:
                trace_fn(msg)
            except Exception:
                pass

    # Validate Gemini config
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY environment variable missing.")
    gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    gemini_endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{gemini_model}:generateContent?key={gemini_api_key}"
    )

    # Ensure sorted unique pages
    pages_to_transcribe = sorted(set(page_numbers))
    if not pages_to_transcribe:
        return {}

    rate_mgr = GeminiRateManager()
    result: Dict[int, str] = {}

    # Process pages one by one to keep memory low.
    for page_num in pages_to_transcribe:
        # Check rate decision and acquire slot
        decision = rate_mgr.get_decision()
        if not decision.allowed:
            raise RateLimitPauseRequired(
                resume_at=decision.resume_at,
                reason=decision.reason,
                retry_after=decision.retry_after
            )

        slot = rate_mgr.acquire_request_slot()
        if slot is None:
            # No slot available – pause
            raise RateLimitPauseRequired(
                resume_at=time.time() + 30,
                reason="no_slot_available"
            )

        try:
            # Render just this page
            images = convert_from_path(
                file_path,
                first_page=page_num,
                last_page=page_num,
                dpi=150
            )
            if not images:
                _t(f"[VLM] Page {page_num} could not be rendered")
                continue
            img = images[0]

            # Transcribe the page
            _, text = _transcribe_single_page(
                page_idx=page_num-1,
                image=img,
                gemini_endpoint=gemini_endpoint,
                rate_mgr=rate_mgr,
                trace_fn=trace_fn,
                max_retries=3
            )
            if text is not None:
                result[page_num] = text
            else:
                _t(f"[VLM] Page {page_num} transcription failed")
        except RateLimitPauseRequired:
            raise
        except Exception as e:
            _t(f"[VLM] Error processing page {page_num}: {e}")
            # Don't raise; skip this page, allow continuation
        finally:
            if slot is not None:
                rate_mgr.release_request_slot(slot)

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Legacy wrapper for backward compatibility (deprecated)
# ─────────────────────────────────────────────────────────────────────────────
def execute_vlm_extraction_step(
    file_path: str,
    pipeline_id: int,
    trace_fn: Optional[Callable] = None,
    progress_json: Optional[Dict[str, Any]] = None,
    on_page_completed: Optional[Callable[[int, Dict[str, Any]], None]] = None,
) -> str:
    """
    Legacy wrapper for backward compatibility. It transcribes all pages that are
    not yet marked as completed in progress_json (if provided) and returns a
    concatenated string of ONLY the newly transcribed pages (no placeholders).
    Pages that were already completed or failed are omitted entirely.
    The worker is responsible for updating progress_json and persisting the
    full document.

    This function is deprecated; new code should use transcribe_pages() directly.
    """
    def _t(msg: str):
        if trace_fn:
            try:
                trace_fn(msg)
            except Exception:
                pass

    # Determine total pages and completed pages
    try:
        with open(file_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            total_pages = len(reader.pages)
    except Exception as e:
        raise RuntimeError(f"Failed to read PDF: {e}")

    completed_pages = set(progress_json.get("completed_pages", []) if progress_json else [])
    # Filter out invalid page numbers
    completed_pages = {p for p in completed_pages if 1 <= p <= total_pages}

    # Determine which pages to transcribe
    remaining_pages = [p for p in range(1, total_pages + 1) if p not in completed_pages]

    _t(f"[VLM] Legacy wrapper: total={total_pages}, completed={len(completed_pages)}, remaining={len(remaining_pages)}")

    # Transcribe only the remaining pages
    new_transcriptions = {}
    if remaining_pages:
        new_transcriptions = transcribe_pages(file_path, remaining_pages, trace_fn)

    # Call the callback for each newly transcribed page
    if on_page_completed:
        for page_num, text in new_transcriptions.items():
            on_page_completed(page_num, {"text": text, "source": "gemini"})

    # Build a string of only the newly transcribed pages, with page breaks.
    # No placeholders for already completed or failed pages.
    page_texts = [text for page_num, text in sorted(new_transcriptions.items())]
    if page_texts:
        result = "\n\n<--- PAGE_BREAK --->\n\n".join(page_texts)
        _t(f"[VLM] Legacy wrapper returning {len(page_texts)} new pages")
        return result
    else:
        _t("[VLM] Legacy wrapper: no new pages transcribed")
        return ""