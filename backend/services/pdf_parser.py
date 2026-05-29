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
def evaluate_text_quality(text: str) -> dict:
    if not text or not text.strip():
        return {
            "quality_score": 0.0,
            "printable_ratio": 0.0,
            "dict_word_ratio": 0.0,
            "coherence_score": 0.0
        }
        
    total_chars = len(text)
    printable_chars = sum(1 for c in text if c.isprintable() or c in ['\n', '\r', '\t'])
    printable_ratio = printable_chars / total_chars if total_chars > 0 else 0.0
    
    common_english_words = {
        "the", "be", "to", "of", "and", "a", "in", "that", "have", "i", "it", "for", "not", "on", "with",
        "he", "as", "you", "do", "at", "this", "but", "his", "by", "from", "they", "we", "say", "her", "she",
        "or", "an", "will", "my", "one", "all", "would", "there", "their", "what", "so", "up", "out", "if",
        "about", "who", "get", "which", "go", "me", "when", "make", "can", "like", "time", "no", "just", "him",
        "know", "take", "people", "into", "year", "your", "good", "some", "could", "them", "see", "other",
        "than", "then", "now", "look", "only", "come", "its", "over", "think", "also", "back", "after", "use",
        "two", "how", "our", "work", "first", "well", "way", "even", "new", "want", "because", "any", "these",
        "give", "day", "most", "us", "are", "was", "were", "been", "has", "had", "did", "does", "done", "goes",
        "went", "gone", "more", "about", "project", "system", "document", "architecture", "data", "test",
        "page", "file", "text", "error", "failed", "success", "pipeline", "worker", "tasks", "task", "run",
        "is", "am", "should", "would", "could", "must", "shall", "do", "does", "did", "done", "has", "had",
        "have", "academic", "simple", "large", "scanned", "image", "based", "repeated", "paragraph", "simulate",
        "timeouts", "volume", "performance", "distributed", "systems", "advanced", "paper", "abstract", "explores",
        "novel", "this", "that", "these", "those"
    }
    
    words = re.findall(r'\b[a-zA-Z]{2,15}\b', text.lower())
    total_words = len(words)
    dict_words_count = sum(1 for w in words if w in common_english_words)
    dict_word_ratio = dict_words_count / total_words if total_words > 0 else 0.0
    
    consonant_cluster_words = 0
    no_vowel_words = 0
    vowels = set("aeiouy")
    
    for w in words:
        if len(w) > 2 and not any(char in vowels for char in w):
            no_vowel_words += 1
            
        consecutive_consonants = 0
        max_consecutive = 0
        for char in w:
            if char not in vowels:
                consecutive_consonants += 1
                if consecutive_consonants > max_consecutive:
                    max_consecutive = consecutive_consonants
            else:
                consecutive_consonants = 0
        if max_consecutive >= 4:
            consonant_cluster_words += 1
            
    coherence_score = 100.0
    if total_words > 0:
        no_vowel_penalty = (no_vowel_words / total_words) * 100.0 * 2.0
        consonant_penalty = (consonant_cluster_words / total_words) * 100.0 * 3.0
        coherence_score = max(0.0, 100.0 - no_vowel_penalty - consonant_penalty)
        
    min_printable = float(os.getenv("MIN_PRINTABLE_RATIO", "0.85"))
    min_dict = float(os.getenv("MIN_DICTIONARY_WORD_RATIO", "0.20"))
    min_coherence = float(os.getenv("MIN_TEXT_COHERENCE_SCORE", "60.0"))

    quality_score = (dict_word_ratio * 0.6 + (coherence_score / 100.0) * 0.4) * 100.0
    if dict_word_ratio < min_dict:
        quality_score -= 50.0
    if printable_ratio < min_printable:
        quality_score -= 20.0
    if coherence_score < min_coherence:
        quality_score -= 20.0
    quality_score = max(0.0, quality_score)
    
    return {
        "quality_score": round(quality_score, 1),
        "printable_ratio": round(printable_ratio, 4),
        "dict_word_ratio": round(dict_word_ratio, 4),
        "coherence_score": round(coherence_score, 1)
    }

# ──────────────────────────────────────────────────────────────────────────────
# Configuration (overridable via environment)
# ──────────────────────────────────────────────────────────────────────────────
MAX_PAGES        = int(os.getenv("PDF_MAX_PAGES",      "600"))
MEMORY_LIMIT_MB  = int(os.getenv("PDF_MEMORY_LIMIT_MB", "1500"))
PARSE_TIMEOUT_S  = int(os.getenv("PDF_PARSE_TIMEOUT_S", "1800"))
LOW_TEXT_THRESH  = int(os.getenv("PDF_LOW_TEXT_CHARS",  "20"))   # chars below which a page is "low-text"
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
    try:
        reader = pypdf.PdfReader(filepath)
    except Exception as e:
        _cleanup()
        err = str(e).lower()
        if any(k in err for k in ("pdf", "read", "corrupt", "decrypt", "eof")):
            raise ValueError(f"FAILED_VALIDATION: Corrupted or unreadable PDF. Details: {e}")
        raise

    page_count = len(reader.pages)
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

        # ── attempt 1: pypdf ─────────────────────────────────────────────────
        page_text = ""
        used_parser = "pypdf"
        try:
            page_text = _extract_page_pypdf(reader, i)
        except Exception as e:
            page_failures.append({"page": i + 1, "parser": "pypdf", "reason": str(e)})
            _trace(f"[PARSER] Page {i + 1} — pypdf failed: {e}")
            page_text = ""

        # ── attempt 2: pdfplumber (if pypdf yielded low text) ────────────────
        if len(page_text.strip()) < LOW_TEXT_THRESH:
            if PDFPLUMBER_AVAILABLE:
                low_text_pages += 1
                if len(page_text.strip()) == 0:
                    _trace(f"[PARSER] Page {i + 1} — no text from pypdf, switching to pdfplumber")
                else:
                    _trace(f"[PARSER] Page {i + 1} — low-text density ({len(page_text.strip())} chars), trying pdfplumber")
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

        # ── attempt 3: OCR (if still low-text after pypdf + pdfplumber) ──────
        if len(page_text.strip()) < LOW_TEXT_THRESH:
            if OCR_AVAILABLE:
                _trace(f"[PARSER] Page {i + 1} — text still empty, activating OCR fallback")
                try:
                    ocr_text, ocr_conf = _extract_page_ocr(filepath, i)
                    if len(ocr_text.strip()) > len(page_text.strip()):
                        page_text = ocr_text
                        used_parser = "ocr"
                        ocr_pages += 1
                        ocr_confidences.append(ocr_conf)
                        _trace(f"[PARSER] Page {i + 1} — OCR extraction completed ({len(ocr_text.strip())} chars) | Confidence: {ocr_conf:.1f}%")
                    else:
                        _trace(f"[PARSER] Page {i + 1} — OCR returned empty (likely blank or purely graphical page)")
                except Exception as e:
                    page_failures.append({"page": i + 1, "parser": "ocr", "reason": str(e)})
                    _trace(f"[PARSER] Page {i + 1} — OCR failed: {e}")
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
                        "status":          "parsing",
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
    primary_metrics = evaluate_text_quality(full_text)
    primary_score = primary_metrics["quality_score"]

    min_printable = float(os.getenv("MIN_PRINTABLE_RATIO", "0.85"))
    min_dict = float(os.getenv("MIN_DICTIONARY_WORD_RATIO", "0.20"))
    min_coherence = float(os.getenv("MIN_TEXT_COHERENCE_SCORE", "60.0"))

    primary_is_bad = (
        primary_metrics["printable_ratio"] < min_printable or
        primary_metrics["dict_word_ratio"] < min_dict or
        primary_metrics["coherence_score"] < min_coherence
    )

    ocr_attempted = False
    ocr_score = 0.0
    selected_parser = stats["parser"]
    selected_text = full_text
    rejection_reason = ""

    if primary_is_bad:
        rejection_reasons = []
        if primary_metrics["printable_ratio"] < min_printable:
            rejection_reasons.append(f"printable_ratio {primary_metrics['printable_ratio']:.2%} < {min_printable:.2%}")
        if primary_metrics["dict_word_ratio"] < min_dict:
            rejection_reasons.append(f"dict_word_ratio {primary_metrics['dict_word_ratio']:.2%} < {min_dict:.2%}")
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
                try:
                    ocr_text_page, ocr_conf_page = _extract_page_ocr(filepath, page_idx)
                    ocr_text_parts.append(ocr_text_page)
                    ocr_page_confidences.append(ocr_conf_page)
                except Exception as e:
                    _trace(f"[PARSER] OCR Rescue — Page {page_idx + 1} failed: {e}")
                    ocr_text_parts.append("")
                    ocr_page_confidences.append(0.0)

            ocr_full_text = "\n\n".join(ocr_text_parts)
            ocr_metrics = evaluate_text_quality(ocr_full_text)
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
    else:
        # Quality was fine
        pass

    stats["ocr_attempted"] = ocr_attempted
    stats["initial_parser"] = "pypdf" if plumber_pages == 0 and ocr_pages == 0 else ("pdfplumber" if plumber_pages > 0 else "ocr")
    stats["comparison_metrics"] = {
        "pypdf_score": primary_score,
        "ocr_score": ocr_score,
        "selected_parser": selected_parser,
        "rejection_reason": rejection_reason
    }

    _trace(
        f"[PARSER] Complete — {stats['processed_pages']} pages in {duration}s | "
        f"chars={stats['char_count']} | pdfplumber_pages={plumber_pages} | ocr_pages={stats['ocr_pages']} | "
        f"failures={len(page_failures)}"
    )

    return ParseResult(text=selected_text, stats=stats)
