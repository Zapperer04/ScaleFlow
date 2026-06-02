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
from typing import Callable, Optional

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Quality Evaluation Helper
# ──────────────────────────────────────────────────────────────────────────────
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from services.quality_gate_service import evaluate_text_quality

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
    except Exception:
        pass
    return 0.0


# ──────────────────────────────────────────────────────────────────────────────
# Per-page extraction helpers
# ──────────────────────────────────────────────────────────────────────────────
def _extract_page_pypdf(reader, page_index: int) -> str:
    """Extract text from a single page using pypdf."""
    try:
        text = reader.pages[page_index].extract_text() or ""
        return text
    except Exception as e:
        raise RuntimeError(f"pypdf page {page_index + 1} error: {e}") from e


def _extract_page_pdfplumber(filepath: str, page_index: int) -> str:
    """Extract text from a single page using pdfplumber."""
    import pdfplumber
    try:
        with pdfplumber.open(filepath) as pdf:
            page = pdf.pages[page_index]
            return page.extract_text() or ""
    except Exception as e:
        raise RuntimeError(f"pdfplumber page {page_index + 1} error: {e}") from e


def _extract_page_ocr(filepath: str, page_index: int) -> tuple[str, float]:
    """Rasterize a PDF page and run Tesseract OCR on it."""
    import pytesseract
    from pdf2image import convert_from_path
    from pytesseract import Output
    try:
        images = convert_from_path(
            filepath,
            first_page=page_index + 1,
            last_page=page_index + 1,
            dpi=200
        )
        if not images:
            return "", 0.0
        
        # Get average OCR confidence for the page words
        try:
            data = pytesseract.image_to_data(images[0], output_type=Output.DICT)
            confidences = [float(c) for c in data.get('conf', []) if c is not None and str(c).strip() != '' and float(c) != -1]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 100.0
        except Exception:
            avg_confidence = 100.0
            
        ocr_text = pytesseract.image_to_string(images[0], config="--psm 6")
        return ocr_text, avg_confidence
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
) -> ParseResult:
    """
    Parse a PDF file using the 3-tier fallback chain.

    Parameters
    ----------
    filepath     : absolute path to the PDF file
    task_id      : orchestration task ID (for progress PATCH + trace emission)
    lease_token  : lease token for progress PATCH
    progress_json: existing progress dict (for resume from checkpoint)
    trace_fn     : callable(message: str) — receives human-readable trace lines
    api_url      : backend API base URL (for progress PATCH)
    api_headers  : auth headers for progress PATCH

    Returns
    -------
    ParseResult with .text and .stats
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

    _trace(f"[PARSER] pypdf extraction started — processing {page_count - checkpoint_page} pages")

    for i in range(checkpoint_page, page_count):
        # ── timeout guard ────────────────────────────────────────────────────
        elapsed = time.time() - start_time
        if elapsed > PARSE_TIMEOUT_S:
            _cleanup()
            raise TimeoutError(f"PDF parse timeout exceeded ({PARSE_TIMEOUT_S}s) at page {i + 1}")

        # ── memory guard (every N pages) ─────────────────────────────────────
        if (i - checkpoint_page) % MEMORY_CHECK_EVERY == 0 and i > checkpoint_page:
            rss = _rss_mb()
            if rss > MEMORY_LIMIT_MB:
                _trace(f"[PARSER] MEMORY GUARD: {rss:.0f} MB RSS at page {i + 1} — raising error to prevent OOM")
                _cleanup()
                raise MemoryError(f"Governance Limit Exceeded: Parser memory usage ({rss:.0f} MB) exceeded limit ({MEMORY_LIMIT_MB} MB).")

        # ── fallback chain loop ──────────────────────────────────────────────
        page_text = ""
        used_parser = ""
        
        t_route_start = time.perf_counter()
        priorities = list(config.PARSER_PRIORITIES)
        t_route_end = time.perf_counter()
        parser_selection_overhead += t_route_end - t_route_start

        for parser_name in priorities:
            # If we've successfully extracted text above threshold, skip subsequent fallback parsers
            if len(page_text.strip()) >= LOW_TEXT_THRESH:
                break
                
            if parser_name == "pypdf":
                t_sub_start = time.perf_counter()
                try:
                    pypdf_text = _extract_page_pypdf(reader, i)
                    if len(pypdf_text.strip()) > len(page_text.strip()):
                        page_text = pypdf_text
                        used_parser = "pypdf"
                except Exception as e:
                    page_failures.append({"page": i + 1, "parser": "pypdf", "reason": str(e)})
                    _trace(f"[PARSER] Page {i + 1} — pypdf failed: {e}")
                t_sub_end = time.perf_counter()
                pypdf_time += t_sub_end - t_sub_start
                    
            elif parser_name == "pdfplumber":
                if PDFPLUMBER_AVAILABLE:
                    if len(page_text.strip()) == 0:
                        _trace(f"[PARSER] Page {i + 1} — no text extracted yet, trying pdfplumber")
                    else:
                        _trace(f"[PARSER] Page {i + 1} — low-text density ({len(page_text.strip())} chars), trying pdfplumber")
                    t_sub_start = time.perf_counter()
                    try:
                        plumber_text = _extract_page_pdfplumber(filepath, i)
                        if len(plumber_text.strip()) > len(page_text.strip()):
                            page_text = plumber_text
                            used_parser = "pdfplumber"
                            plumber_pages += 1
                            _trace(f"[PARSER] Page {i + 1} — pdfplumber succeeded ({len(plumber_text.strip())} chars)")
                    except Exception as e:
                        page_failures.append({"page": i + 1, "parser": "pdfplumber", "reason": str(e)})
                        _trace(f"[PARSER] Page {i + 1} — pdfplumber failed: {e}")
                    t_sub_end = time.perf_counter()
                    plumber_time += t_sub_end - t_sub_start
                        
            elif parser_name == "ocr":
                if OCR_AVAILABLE:
                    _trace(f"[PARSER] Page {i + 1} — text still empty, activating OCR fallback")
                    t_sub_start = time.perf_counter()
                    try:
                        ocr_text_page, ocr_conf = _extract_page_ocr(filepath, i)
                        if len(ocr_text_page.strip()) > len(page_text.strip()):
                            page_text = ocr_text_page
                            used_parser = "ocr"
                            ocr_pages += 1
                            ocr_confidences.append(ocr_conf)
                            _trace(f"[PARSER] Page {i + 1} — OCR extraction completed ({len(ocr_text_page.strip())} chars) | Confidence: {ocr_conf:.1f}%")
                        else:
                            _trace(f"[PARSER] Page {i + 1} — OCR returned empty (likely blank or purely graphical page)")
                    except Exception as e:
                        page_failures.append({"page": i + 1, "parser": "ocr", "reason": str(e)})
                        _trace(f"[PARSER] Page {i + 1} — OCR failed: {e}")
                    t_sub_end = time.perf_counter()
                    ocr_time += t_sub_end - t_sub_start
                else:
                    _trace(f"[PARSER] Page {i + 1} — scanned/image page detected but OCR unavailable (install pytesseract + pdf2image + poppler)")

        if page_text:
            text_parts.append(page_text)

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
    }

    # ── evaluate primary parse quality ────────────────────────────────────────
    t_qual_start = time.perf_counter()
    primary_metrics = evaluate_text_quality(full_text)
    t_qual_end = time.perf_counter()
    quality_evaluation_time = t_qual_end - t_qual_start
    primary_score = primary_metrics["quality_score"]

    min_printable = config.MIN_PRINTABLE_RATIO
    min_dict = config.MIN_DICTIONARY_WORD_RATIO
    min_coherence = config.MIN_TEXT_COHERENCE_SCORE

    # Use code-aware minimum dictionary word ratio threshold
    effective_min_dict = 0.10 if primary_metrics.get("programming_keyword_score", 0.0) > 3.0 else min_dict

    primary_is_bad = (
        primary_metrics["printable_ratio"] < min_printable or
        primary_metrics["dict_word_ratio"] < effective_min_dict or
        primary_metrics["coherence_score"] < min_coherence
    )

    ocr_attempted = False
    ocr_score = 0.0
    ocr_metrics = {}
    selected_parser = stats["parser"]
    selected_text = full_text
    rejection_reason = ""
    ocr_rescue_evaluation_time = 0.0

    if primary_is_bad:
        rejection_reasons = []
        if primary_metrics["printable_ratio"] < min_printable:
            rejection_reasons.append(f"printable_ratio {primary_metrics['printable_ratio']:.2%} < {min_printable:.2%}")
        if primary_metrics["dict_word_ratio"] < effective_min_dict:
            rejection_reasons.append(f"dict_word_ratio {primary_metrics['dict_word_ratio']:.2%} < {effective_min_dict:.2%}")
        if primary_metrics["coherence_score"] < min_coherence:
            rejection_reasons.append(f"coherence_score {primary_metrics['coherence_score']:.1f} < {min_coherence:.1f}")
        rejection_reason = "Primary parse quality bad: " + "; ".join(rejection_reasons)

        if OCR_AVAILABLE:
            _trace(f"[PARSER] OCR RESCUE: Primary parse failed quality evaluation ({rejection_reason}). Triggering full document OCR rescue pass...")
            ocr_attempted = True
            ocr_text_parts = []
            ocr_page_confidences = []

            for page_idx in range(page_count):
                _trace(f"[PARSER] OCR Rescue — Running OCR on page {page_idx + 1}/{page_count}...")
                t_ocr_sub_start = time.perf_counter()
                try:
                    ocr_text_page, ocr_conf_page = _extract_page_ocr(filepath, page_idx)
                    ocr_text_parts.append(ocr_text_page)
                    ocr_page_confidences.append(ocr_conf_page)
                except Exception as e:
                    _trace(f"[PARSER] OCR Rescue — Page {page_idx + 1} failed: {e}")
                    ocr_text_parts.append("")
                    ocr_page_confidences.append(0.0)
                t_ocr_sub_end = time.perf_counter()
                ocr_time += t_ocr_sub_end - t_ocr_sub_start

            ocr_full_text = "\n\n".join(ocr_text_parts)
            t_eval_start = time.perf_counter()
            ocr_metrics = evaluate_text_quality(ocr_full_text)
            t_eval_end = time.perf_counter()
            ocr_rescue_evaluation_time = t_eval_end - t_eval_start
            ocr_score = ocr_metrics["quality_score"]

            if ocr_score > primary_score:
                _trace(f"[PARSER] OCR Rescue SUCCESS! OCR Quality Score ({ocr_score:.1f}) > Primary Quality Score ({primary_score:.1f}). Selecting OCR parse.")
                selected_text = ocr_full_text
                selected_parser = "ocr"
                # Update stats
                stats["parser"] = "ocr_fallback"
                stats["ocr_pages"] = page_count
                stats["ocr_confidences"] = ocr_page_confidences
                stats["avg_ocr_confidence"] = sum(ocr_page_confidences) / len(ocr_page_confidences) if ocr_page_confidences else 100.0
                stats["char_count"] = len(ocr_full_text)
            else:
                _trace(f"[PARSER] OCR Rescue COMPLETED. OCR Quality Score ({ocr_score:.1f}) is not better than Primary Quality Score ({primary_score:.1f}). Retaining primary parse.")
        else:
            _trace(f"[PARSER] OCR Rescue requested, but OCR is not available on this system.")

    stats["ocr_attempted"] = ocr_attempted
    stats["initial_parser"] = "pypdf" if plumber_pages == 0 and ocr_pages == 0 else ("pdfplumber" if plumber_pages > 0 else "ocr")
    stats["comparison_metrics"] = {
        "pypdf_score": primary_score,
        "ocr_score": ocr_score,
        "selected_parser": selected_parser,
        "rejection_reason": rejection_reason,
        "pypdf_programming_keyword_score": primary_metrics.get("programming_keyword_score", 0.0),
        "ocr_programming_keyword_score": ocr_metrics.get("programming_keyword_score", 0.0) if ocr_metrics else 0.0,
        "pypdf_dict_word_ratio": primary_metrics.get("dict_word_ratio", 0.0),
        "ocr_dict_word_ratio": ocr_metrics.get("dict_word_ratio", 0.0) if ocr_metrics else 0.0,
        "pypdf_coherence_score": primary_metrics.get("coherence_score", 0.0),
        "ocr_coherence_score": ocr_metrics.get("coherence_score", 0.0) if ocr_metrics else 0.0,
        "pypdf_printable_ratio": primary_metrics.get("printable_ratio", 0.0),
        "ocr_printable_ratio": ocr_metrics.get("printable_ratio", 0.0) if ocr_metrics else 0.0,
        "pypdf_ocr_confidence": 100.0,
        "ocr_ocr_confidence": sum(ocr_page_confidences) / len(ocr_page_confidences) if ocr_attempted and ocr_page_confidences else (stats.get("avg_ocr_confidence", 100.0) if stats.get("ocr_pages", 0) > 0 else 100.0)
    }

    # Store timings inside stats dictionary
    stats["timings"] = {
        "pdf_open_time": round(pdf_open_time, 5),
        "page_count_discovery_time": round(page_count_discovery_time, 5),
        "pypdf_extraction_duration": round(pypdf_time, 5),
        "pdfplumber_extraction_duration": round(plumber_time, 5),
        "ocr_duration": round(ocr_time, 5),
        "parser_selection_overhead": round(parser_selection_overhead, 5),
        "parse_quality_evaluation_duration": round(quality_evaluation_time, 5),
        "ocr_rescue_quality_evaluation_duration": round(ocr_rescue_evaluation_time, 5),
    }

    _trace(
        f"[PARSER] Complete — {stats['processed_pages']} pages in {duration}s | "
        f"chars={stats['char_count']} | pdfplumber_pages={plumber_pages} | ocr_pages={stats['ocr_pages']} | "
        f"failures={len(page_failures)}"
    )

    return ParseResult(text=selected_text, stats=stats)
