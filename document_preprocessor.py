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
import re
import math
import io
import tempfile
import hashlib
from urllib.parse import urlparse
import uuid

# Import the centralized rate manager
from services.gemini_rate_manager import GeminiRateManager, RateLimitPauseRequired

logger = logging.getLogger(__name__)

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

from pdf2image import convert_from_path


# ─────────────────────────────────────────────────────────────────────────────
# Persistent Graph Storage (production artifact system)
# ─────────────────────────────────────────────────────────────────────────────
BASE_STORAGE_DIR = getattr(
    config,
    'BASE_STORAGE_DIR',
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'storage')
)
GRAPH_STORAGE_DIR = os.path.join(BASE_STORAGE_DIR, 'graphs')

# Schema version – use semantic versioning (v1.0, v1.1, ...)
GRAPH_SCHEMA_VERSION = getattr(config, 'GRAPH_SCHEMA_VERSION', 'v1.0')
GRAPH_VERSION_SUBDIR = os.path.join(GRAPH_STORAGE_DIR, GRAPH_SCHEMA_VERSION)

try:
    os.makedirs(GRAPH_VERSION_SUBDIR, exist_ok=True)
except Exception as e:
    logger.warning(f"Could not create graph storage directory {GRAPH_VERSION_SUBDIR}: {e}")

# In-memory cache for speed (optional, not relied upon for correctness)
_GRAPH_CACHE = {}  # key: (content_hash, page_range_tuple) -> artifact dict

def _get_content_hash(file_path: str) -> str:
    """
    Compute a stable content hash of the file.
    This is used as the primary key for the graph artifact.
    """
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            hasher.update(chunk)
    return hasher.hexdigest()

def _get_graph_storage_path(content_hash: str) -> str:
    """
    Return the file path for the graph artifact given a content hash.
    Includes version subdirectory.
    """
    return os.path.join(GRAPH_VERSION_SUBDIR, f"{content_hash}.json")

def _store_graph(
    file_path: str,
    pages: List[int],
    graph_pages: List[Dict[str, Any]],
    parser: str = "gemini_vlm",
    version: str = GRAPH_SCHEMA_VERSION,
    timings: Optional[Dict[str, Any]] = None
) -> None:
    """
    Persist the rich document graph as a first-class artifact.
    The graph is stored in a versioned subdirectory, keyed by content hash.
    Also updates the in-memory cache for speed.
    """
    if not graph_pages:
        return

    content_hash = _get_content_hash(file_path)
    cache_key = (content_hash, tuple(sorted(pages)))

    # Build the complete graph artifact with rich metadata
    artifact = {
        "document": {
            "content_hash": content_hash,
            "filename": os.path.basename(file_path),      # only filename, not absolute path
            "pages_requested": pages,
            "timestamp": time.time(),
            "version": version,
            "parser": parser,
        },
        "pages": graph_pages,
        "metadata": {
            "page_count": len(graph_pages),
            "node_count": sum(len(p.get("blocks", [])) for p in graph_pages),
            "parser": parser,
            "schema_version": version,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "model_used": os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        }
    }
    if timings:
        artifact["metadata"]["timings"] = timings

    # Update in-memory cache
    _GRAPH_CACHE[cache_key] = artifact

    # Write to persistent storage
    storage_path = _get_graph_storage_path(content_hash)
    try:
        with open(storage_path, 'w', encoding='utf-8') as f:
            json.dump(artifact, f, ensure_ascii=False, indent=2)
        logger.info(f"Graph artifact persisted to {storage_path}")
    except Exception as e:
        logger.error(f"Failed to persist graph artifact: {e}")
        raise RuntimeError(f"Graph artifact persistence failed: {e}")

def _get_graph_artifact(content_hash: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve the full graph artifact by content hash.
    """
    storage_path = _get_graph_storage_path(content_hash)
    if not os.path.exists(storage_path):
        return None

    try:
        with open(storage_path, 'r', encoding='utf-8') as f:
            artifact = json.load(f)
        # Update cache
        cache_key = (content_hash, tuple(sorted(artifact["document"]["pages_requested"])))
        _GRAPH_CACHE[cache_key] = artifact
        return artifact
    except Exception as e:
        logger.error(f"Failed to load graph artifact: {e}")
        return None

def _get_graph(file_path: str, pages: List[int]) -> Optional[List[Dict[str, Any]]]:
    """
    Retrieve the document graph pages for the given file and pages.
    First checks in-memory cache, then disk.
    Returns None if no graph is found.
    If the stored artifact contains pages beyond those requested, filters to the requested subset.
    If any requested page is missing, returns None to indicate incompleteness.
    """
    content_hash = _get_content_hash(file_path)
    cache_key = (content_hash, tuple(sorted(pages)))
    artifact = None
    if cache_key in _GRAPH_CACHE:
        artifact = _GRAPH_CACHE[cache_key]
    else:
        artifact = _get_graph_artifact(content_hash)
        if artifact:
            _GRAPH_CACHE[cache_key] = artifact

    if not artifact:
        return None

    stored_pages = artifact.get("pages", [])
    requested_set = set(pages)
    # Filter to only the requested pages
    filtered = [p for p in stored_pages if p.get("page") in requested_set]
    # Verify that we have exactly all requested pages
    if len(filtered) != len(requested_set):
        # Some pages are missing; return None to indicate incomplete graph
        return None
    return filtered if filtered else None

# ─────────────────────────────────────────────────────────────────────────────
# Public API for downstream artifact discovery
# ─────────────────────────────────────────────────────────────────────────────
def get_graph_artifact_path(content_hash: str) -> str:
    """
    Return the filesystem path where the graph artifact for the given content hash
    is stored (or would be stored). Useful for downstream consumers that need
    to read the artifact directly.
    """
    return _get_graph_storage_path(content_hash)

def load_graph_artifact(content_hash: str) -> Optional[Dict[str, Any]]:
    """
    Public helper to load the full graph artifact for a document, given its content hash.
    Returns the artifact dict, or None if not found.
    """
    return _get_graph_artifact(content_hash)


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
            _t(f"[PREPROCESS] Document classified as DIGITAL. Pipeline architecture: Gemini VLM-first (coherence={text_coherence_score:.1f})")
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
            _t(f"[PREPROCESS] Document classified as SCANNED. Pipeline architecture: Gemini VLM-first — reasons: {', '.join(reasons)}")

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
# Gemini Files API integration (correct resumable upload)
# ─────────────────────────────────────────────────────────────────────────────

def _get_gemini_api_key_and_model() -> Tuple[str, str]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable missing.")
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    return api_key, model

def _upload_pdf_to_gemini_resumable(file_path: str, trace_fn: Optional[Callable] = None) -> Tuple[str, str]:
    """
    Upload a PDF file to Gemini Files API using the resumable upload protocol.
    Returns (file_uri, file_name).
    """
    def _t(msg: str):
        if trace_fn:
            try:
                trace_fn(msg)
            except Exception:
                pass

    api_key, _ = _get_gemini_api_key_and_model()
    upload_url = f"https://generativelanguage.googleapis.com/upload/v1beta/files?key={api_key}"
    headers = {
        "X-Goog-Upload-Protocol": "resumable",
        "X-Goog-Upload-Command": "start",
        "X-Goog-Upload-Header-Content-Length": str(os.path.getsize(file_path)),
        "Content-Type": "application/json",
    }
    metadata = {
        "file": {
            "display_name": os.path.basename(file_path),
            "mime_type": "application/pdf",
        }
    }
    _t("[GEMINI] Initiating resumable upload...")
    upload_init_timeout = getattr(config, "GEMINI_UPLOAD_INIT_TIMEOUT", 30)
    resp = requests.post(upload_url, headers=headers, json=metadata, timeout=upload_init_timeout)
    if resp.status_code != 200:
        _t(f"[GEMINI] Upload init failed: {resp.status_code}")
        raise RuntimeError(f"Gemini upload init failed: {resp.text}")
    upload_session_url = resp.headers.get("X-Goog-Upload-URL")
    if not upload_session_url:
        if "uploadUrl" in resp.json():
            upload_session_url = resp.json()["uploadUrl"]
        else:
            raise RuntimeError("No upload session URL returned")
    _t("[GEMINI] Resumable upload session created.")

    with open(file_path, "rb") as f:
        file_content = f.read()
    headers = {
        "Content-Length": str(len(file_content)),
        "X-Goog-Upload-Command": "upload, finalize",
        "X-Goog-Upload-Offset": "0",
    }
    upload_content_timeout = getattr(config, "GEMINI_UPLOAD_CONTENT_TIMEOUT", 120)
    resp2 = requests.post(upload_session_url, headers=headers, data=file_content, timeout=upload_content_timeout)
    if resp2.status_code != 200:
        _t(f"[GEMINI] Upload content failed: {resp2.status_code}")
        raise RuntimeError(f"Gemini upload content failed: {resp2.text}")
    result = resp2.json()
    file_uri = result.get("file", {}).get("uri")
    file_name = result.get("file", {}).get("name")
    if not file_uri or not file_name:
        raise RuntimeError("Gemini upload response missing uri/name")
    _t("[GEMINI] Upload completed successfully.")
    return file_uri, file_name


def _delete_gemini_file(file_name: str, trace_fn: Optional[Callable] = None) -> None:
    """Delete a file from Gemini Files API. 404 is treated as success."""
    def _t(msg: str):
        if trace_fn:
            try:
                trace_fn(msg)
            except Exception:
                pass
    api_key, _ = _get_gemini_api_key_and_model()
    url = f"https://generativelanguage.googleapis.com/v1beta/files/{file_name}?key={api_key}"
    try:
        resp = requests.delete(url, timeout=30)
        if resp.status_code == 404:
            _t("[GEMINI] Temporary file already removed.")
            return
        if resp.status_code not in (200, 204):
            _t(f"[GEMINI] Delete file failed: {resp.status_code}")
        else:
            _t("[GEMINI] Temporary file deleted.")
    except Exception as e:
        _t(f"[GEMINI] Error deleting file: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Gemini generateContent with PDF URI and JSON response
# ─────────────────────────────────────────────────────────────────────────────

def _call_gemini_with_pdf(
    file_uri: str,
    prompt: str,
    gemini_model: str,
    api_key: str,
    trace_fn: Optional[Callable] = None,
    max_retries: int = 3,
) -> Dict[str, Any]:
    """
    Send a request to Gemini with a file URI and a text prompt.
    Returns parsed JSON response (dict). The response must contain a "pages" key.
    Raises RateLimitPauseRequired or Exception.
    """
    def _t(msg: str):
        if trace_fn:
            try:
                trace_fn(msg)
            except Exception:
                pass

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={api_key}"
    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {"fileData": {"mimeType": "application/pdf", "fileUri": file_uri}}
            ]
        }],
        "generationConfig": {
            "temperature": 0.0,
            "responseMimeType": "application/json"
        }
    }

    timeout_seconds = getattr(config, "GEMINI_GENERATE_TIMEOUT", 240)

    last_error = None
    for attempt in range(max_retries):
        try:
            resp = requests.post(url, headers={"Content-Type": "application/json"}, json=payload, timeout=timeout_seconds)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    raise ValueError("No candidates in response")
                finish_reason = candidates[0].get("finishReason")
                if finish_reason != "STOP":
                    _t(f"[GEMINI] finishReason={finish_reason} (not STOP)")
                    if finish_reason in ("SAFETY", "RECITATION"):
                        raise ValueError(f"Gemini safety/recitation block: {finish_reason}")
                    if finish_reason == "MAX_TOKENS":
                        raise ValueError("finishReason=MAX_TOKENS (chunk too large)")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    else:
                        raise ValueError(f"finishReason={finish_reason}")
                parts = candidates[0].get("content", {}).get("parts", [])
                if not parts:
                    raise ValueError("No parts in content")
                text = parts[0].get("text", "")
                try:
                    parsed = json.loads(text)
                except json.JSONDecodeError as e:
                    _t(f"[GEMINI] JSON parse error: {e}. Raw text: {text[:500]}")
                    cleaned = re.sub(r"^```json\s*", "", text)
                    cleaned = re.sub(r"\s*```$", "", cleaned)
                    try:
                        parsed = json.loads(cleaned)
                    except:
                        raise ValueError(f"Invalid JSON response: {e}")
                if not isinstance(parsed, dict):
                    raise ValueError("Response is not a JSON object")
                if "pages" not in parsed:
                    if isinstance(parsed, list):
                        parsed = {"pages": parsed}
                    else:
                        raise ValueError("Response JSON missing 'pages' key")
                if not isinstance(parsed["pages"], list):
                    raise ValueError("'pages' is not a list")
                for p in parsed["pages"]:
                    if "page" not in p:
                        raise ValueError("Page object missing 'page'")
                    if "text" not in p and "blocks" not in p:
                        raise ValueError("Page object missing 'text' or 'blocks'")
                    # Allow simplified schema; we'll transform later
                return parsed
            elif resp.status_code in (429, 503) or "quota" in resp.text.lower() or "rate limit" in resp.text.lower():
                retry_after = 60.0
                try:
                    retry_after = float(resp.headers.get("Retry-After", 60.0))
                except:
                    pass
                _t(f"[GEMINI] Rate limit hit. Retry after {retry_after}s")
                raise RateLimitPauseRequired(resume_at=time.time() + retry_after, reason="rate_limit", retry_after=retry_after)
            else:
                if resp.status_code in (500, 502, 504):
                    sleep_time = 2 ** attempt
                    _t(f"[GEMINI] Server error {resp.status_code}. Retrying in {sleep_time}s...")
                    time.sleep(sleep_time)
                    continue
                else:
                    _t(f"[GEMINI] HTTP error: {resp.status_code}")
                    raise RuntimeError(f"Gemini API error: {resp.status_code}")
        except RateLimitPauseRequired:
            raise
        except requests.exceptions.Timeout as e:
            _t(f"[GEMINI] Request timeout. Retry attempt {attempt+1}/{max_retries}")
            last_error = e
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise
        except requests.exceptions.ConnectionError as e:
            _t(f"[GEMINI] Connection error. Retry attempt {attempt+1}/{max_retries}")
            last_error = e
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise
        except Exception as e:
            last_error = e
            _t(f"[GEMINI] Call failed: {e}. Retry attempt {attempt+1}/{max_retries}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise
    raise RuntimeError(f"Gemini call failed after {max_retries} attempts: {last_error}")


# ─────────────────────────────────────────────────────────────────────────────
# Adaptive Planning
# ─────────────────────────────────────────────────────────────────────────────

MAX_PAGES_WHOLE = 30
MAX_FILE_SIZE_WHOLE = 20 * 1024 * 1024
# Use configurable batch size; default to 8 for better response size management
MAX_PAGES_PER_BATCH = getattr(config, "MAX_VLM_BATCH_PAGES", 8)

def _estimate_tokens_from_pdf(file_path: str, pages: List[int]) -> int:
    size = os.path.getsize(file_path)
    tokens = int(size / 20)  # rough
    tokens += len(pages) * 200
    return tokens

def _adaptive_plan(
    file_path: str,
    pages_to_transcribe: List[int],
    report: Optional[PreprocessingReport] = None,
) -> Dict[str, Any]:
    num_pages = len(pages_to_transcribe)
    file_size = os.path.getsize(file_path)
    is_scanned = report and report.document_type == "SCANNED"

    if num_pages <= MAX_PAGES_WHOLE and file_size <= MAX_FILE_SIZE_WHOLE and not is_scanned:
        estimated_tokens = _estimate_tokens_from_pdf(file_path, pages_to_transcribe)
        if estimated_tokens < 700000:
            return {"strategy": "whole", "page_list": pages_to_transcribe}

    batch_size = MAX_PAGES_PER_BATCH
    if is_scanned:
        batch_size = min(batch_size, 6)  # scanned docs may be heavier

    pages_sorted = sorted(pages_to_transcribe)
    segments = []
    start = pages_sorted[0]
    end = start
    for p in pages_sorted[1:]:
        if p == end + 1:
            end = p
        else:
            segments.append((start, end))
            start = p
            end = p
    segments.append((start, end))

    batches = []
    for seg_start, seg_end in segments:
        for i in range(seg_start, seg_end + 1, batch_size):
            chunk_end = min(i + batch_size - 1, seg_end)
            batches.append(list(range(i, chunk_end + 1)))

    return {"strategy": "batch", "batches": batches}


def _split_pdf_to_temp_chunk(file_path: str, start_page: int, end_page: int) -> str:
    with open(file_path, "rb") as f:
        reader = pypdf.PdfReader(f)
        writer = pypdf.PdfWriter()
        for p in range(start_page-1, end_page):
            writer.add_page(reader.pages[p])
        fd, out_path = tempfile.mkstemp(suffix=".pdf", prefix="chunk_")
        os.close(fd)
        with open(out_path, "wb") as fw:
            writer.write(fw)
    return out_path


# ─────────────────────────────────────────────────────────────────────────────
# Helper to determine if an exception is a batch-size failure (should trigger subdivision)
# ─────────────────────────────────────────────────────────────────────────────
def _is_batch_size_failure(exc: Exception) -> bool:
    """Return True if the exception indicates the batch was too large and should be split."""
    # Catch explicit timeouts
    if isinstance(exc, requests.exceptions.Timeout):
        return True
    # Catch connection errors that might be due to timeouts
    if isinstance(exc, requests.exceptions.ConnectionError):
        error_str = str(exc).lower()
        if "timeout" in error_str or "read timed out" in error_str:
            return True
    # Check error message for timeout indicators
    error_str = str(exc).lower()
    if "timeout" in error_str or "read timed out" in error_str:
        return True
    # Check for MAX_TOKENS or payload too large
    if isinstance(exc, ValueError):
        msg = str(exc).lower()
        # Safety/recitation blocks are content issues, not batch-size
        if "safety" in msg or "recitation" in msg:
            return False
        if "max_tokens" in msg or "payload too large" in msg or "response too large" in msg:
            return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Core Adaptive Transcription Engine (using Files API)
# ─────────────────────────────────────────────────────────────────────────────

def _execute_adaptive_transcription(
    file_path: str,
    pages_to_transcribe: List[int],
    trace_fn: Optional[Callable] = None,
    report: Optional[PreprocessingReport] = None,
) -> Dict[int, str]:
    """
    Transcribe pages using adaptive strategy with Gemini Files API.
    Returns dict mapping page_num to text.
    Raises RateLimitPauseRequired if rate limit encountered.
    All uploaded files are deleted after use to prevent leaks.
    The full graph (blocks, tables, bbox, etc.) is persisted as a first‑class
    artifact in the shared storage, keyed by content hash.
    """
    def _t(msg: str):
        if trace_fn:
            try:
                trace_fn(msg)
            except Exception:
                pass

    if not pages_to_transcribe:
        return {}

    api_key, model = _get_gemini_api_key_and_model()
    plan = _adaptive_plan(file_path, pages_to_transcribe, report)
    strategy = plan["strategy"]
    _t(f"[ADAPTIVE] Strategy: {strategy} for {len(pages_to_transcribe)} pages")

    rate_mgr = GeminiRateManager()
    result: Dict[int, str] = {}
    all_graph_pages = []  # accumulate graph data for caching
    page_parser_map: Dict[int, str] = {}  # page -> parser
    overall_timings = {}  # collect timings for the whole transcription
    start_time = time.perf_counter()

    # Telemetry counters
    total_batches_attempted = 0
    max_batch_size_attempted = 0
    min_batch_size_attempted = float('inf')
    batch_history = []  # list of dicts with size, upload, generate, parse

    # Helper to process a PDF file (whole or batch) with timing
    def _process_pdf_file(pdf_path: str, pages_in_chunk: List[int], is_whole: bool, parser_name: str = "gemini_vlm") -> Tuple[Dict[int, str], List[Dict[str, Any]], Dict[str, float]]:
        local_text = {}
        local_graph = []
        timings = {}
        file_uri = None
        file_name = None
        try:
            # Upload timing
            upload_start = time.perf_counter()
            slot = rate_mgr.acquire_request_slot()
            if slot is None:
                raise RateLimitPauseRequired(resume_at=time.time() + 30, reason="no_slot_available")
            try:
                file_uri, file_name = _upload_pdf_to_gemini_resumable(pdf_path, trace_fn)
            finally:
                if slot:
                    rate_mgr.release_request_slot(slot)
            timings["upload_secs"] = time.perf_counter() - upload_start

            prompt = _build_graph_extraction_prompt(pages_in_chunk, is_whole)

            # GenerateContent timing
            generate_start = time.perf_counter()
            slot2 = rate_mgr.acquire_request_slot()
            if slot2 is None:
                raise RateLimitPauseRequired(resume_at=time.time() + 30, reason="no_slot_available")
            try:
                parsed = _call_gemini_with_pdf(file_uri, prompt, model, api_key, trace_fn)
            finally:
                if slot2:
                    rate_mgr.release_request_slot(slot2)
            timings["generate_secs"] = time.perf_counter() - generate_start

            # JSON parsing timing
            parse_start = time.perf_counter()
            for pobj in parsed["pages"]:
                pnum = pobj["page"]
                if pnum in pages_in_chunk:
                    # Transform simplified schema into full graph format
                    page_graph = _transform_to_graph_page(pnum, pobj)
                    local_text[pnum] = page_graph["text"]
                    local_graph.append(page_graph)
                    page_parser_map[pnum] = parser_name
                else:
                    _t(f"[ADAPTIVE] Received page {pnum} not in requested list; ignoring")
            timings["parse_secs"] = time.perf_counter() - parse_start
            timings["batch_pages_requested"] = len(pages_in_chunk)
        except RateLimitPauseRequired:
            raise
        except Exception as e:
            _t(f"[ADAPTIVE] PDF processing failed: {e}")
            raise
        finally:
            if file_name:
                _delete_gemini_file(file_name, trace_fn)
        return local_text, local_graph, timings

    def _transform_to_graph_page(page_num: int, raw_page: Dict[str, Any]) -> Dict[str, Any]:
        """Convert simplified page schema to full graph page format with defaults."""
        text = raw_page.get("text", "")
        raw_blocks = raw_page.get("blocks", [])
        raw_tables = raw_page.get("tables", [])

        # Build blocks with default bbox and confidence
        blocks = []
        for idx, rb in enumerate(raw_blocks):
            block_type = rb.get("type", "paragraph")
            block_text = rb.get("text", "")
            blocks.append({
                "type": block_type,
                "text": block_text,
                "bbox": [0.0, 0.0, 1.0, 1.0],
                "reading_order": idx,
                "confidence": 0.9,
                "children": []
            })

        # Build tables with default bbox
        tables = []
        for rt in raw_tables:
            tables.append({
                "caption": rt.get("caption", ""),
                "headers": rt.get("headers", []),
                "rows": rt.get("rows", []),
                "bbox": [0.0, 0.0, 1.0, 1.0]
            })

        # Reading order as list of indices
        reading_order = list(range(len(blocks)))

        return {
            "page": page_num,
            "text": text,
            "blocks": blocks,
            "tables": tables,
            "reading_order": reading_order
        }

    # Recursive batch processing with adaptive subdivision
    recursion_depth = 0
    subdivision_count = 0
    max_depth_reached = 0

    def _process_batch_recursive(batch_pages: List[int], depth: int = 0) -> None:
        nonlocal recursion_depth, subdivision_count, max_depth_reached
        nonlocal total_batches_attempted, max_batch_size_attempted, min_batch_size_attempted, batch_history
        recursion_depth = max(recursion_depth, depth)
        if not batch_pages:
            return
        if len(batch_pages) == 1:
            # Single page fallback (last resort after all subdivision)
            p = batch_pages[0]
            _t(f"[ADAPTIVE] Processing single page {p} via image fallback")
            page_text = _transcribe_single_page_fallback(file_path, p, trace_fn, rate_mgr)
            if page_text:
                result[p] = page_text
                minimal_page = {
                    "page": p,
                    "text": page_text,
                    "blocks": [
                        {
                            "type": "paragraph",
                            "text": page_text,
                            "bbox": [0.0, 0.0, 1.0, 1.0],
                            "reading_order": 1,
                            "confidence": 0.8,
                            "children": []
                        }
                    ],
                    "tables": [],
                    "reading_order": [0]
                }
                all_graph_pages.append(minimal_page)
                page_parser_map[p] = "tesseract_ocr"
            return

        # Attempt to process as a batch (contiguous range)
        chunk_path = None
        try:
            # We need a contiguous range for chunking; assume batch_pages is sorted and contiguous
            if batch_pages == list(range(batch_pages[0], batch_pages[-1]+1)):
                total_batches_attempted += 1
                batch_size = len(batch_pages)
                max_batch_size_attempted = max(max_batch_size_attempted, batch_size)
                min_batch_size_attempted = min(min_batch_size_attempted, batch_size)

                chunk_path = _split_pdf_to_temp_chunk(file_path, batch_pages[0], batch_pages[-1])
                text_dict, graph_list, timings = _process_pdf_file(chunk_path, batch_pages, is_whole=False, parser_name="gemini_vlm")
                result.update(text_dict)
                all_graph_pages.extend(graph_list)

                # Record batch telemetry
                batch_entry = {
                    "size": batch_size,
                    "upload_secs": timings.get("upload_secs", 0),
                    "generate_secs": timings.get("generate_secs", 0),
                    "parse_secs": timings.get("parse_secs", 0),
                }
                batch_history.append(batch_entry)

                # Accumulate timings
                for k, v in timings.items():
                    if k != "batch_pages_requested":
                        overall_timings.setdefault(k, 0.0)
                        overall_timings[k] += v
                overall_timings[f"batch_{batch_size}_pages"] = timings.get("generate_secs", 0)
                _t(f"[ADAPTIVE] Batch of {batch_size} pages succeeded.")
                return
            else:
                # Non-contiguous – fallback to recursive split
                _t(f"[ADAPTIVE] Batch {batch_pages} not contiguous; splitting.")
        except RateLimitPauseRequired:
            raise  # Never split on rate limits
        except Exception as e:
            # Only split if it's a batch-size failure
            if _is_batch_size_failure(e):
                _t(f"[ADAPTIVE] Batch of {len(batch_pages)} pages failed (batch-size issue): {e}. Splitting.")
            else:
                _t(f"[ADAPTIVE] Batch of {len(batch_pages)} pages failed with non-recoverable error: {e}. Raising.")
                raise
        finally:
            if chunk_path and os.path.exists(chunk_path):
                try:
                    os.remove(chunk_path)
                except:
                    pass

        # Split into two halves and recurse
        mid = len(batch_pages) // 2
        left = batch_pages[:mid]
        right = batch_pages[mid:]
        subdivision_count += 1
        _t(f"[ADAPTIVE] Subdividing {len(batch_pages)} → {len(left)} + {len(right)} (subdivision #{subdivision_count})")
        _process_batch_recursive(left, depth+1)
        _process_batch_recursive(right, depth+1)

    if strategy == "whole":
        try:
            text_dict, graph_list, timings = _process_pdf_file(file_path, pages_to_transcribe, is_whole=True, parser_name="gemini_vlm")
            result.update(text_dict)
            all_graph_pages.extend(graph_list)
            overall_timings.update(timings)
            _t(f"[ADAPTIVE] Whole document parsed, got {len(result)} pages")
        except RateLimitPauseRequired:
            raise
        except Exception as e:
            _t(f"[ADAPTIVE] Whole document failed: {e}. Falling back to batch mode.")
            plan = {"strategy": "batch", "batches": [sorted(pages_to_transcribe)]}

    if strategy == "batch" or (strategy == "whole" and not result):
        batches = plan.get("batches", [])
        if not batches:
            batches = [sorted(pages_to_transcribe)]
        _t(f"[ADAPTIVE] Batch mode: {len(batches)} batches")
        for batch in batches:
            _process_batch_recursive(batch)

    # Fallback for any missing pages (if still missing) – this is a safety net
    missing = set(pages_to_transcribe) - set(result.keys())
    if missing:
        _t(f"[ADAPTIVE] Missing pages: {missing}; falling back to single-page fallback")
        for p in sorted(missing):
            try:
                page_text = _transcribe_single_page_fallback(file_path, p, trace_fn, rate_mgr)
                if page_text:
                    result[p] = page_text
                    minimal_page = {
                        "page": p,
                        "text": page_text,
                        "blocks": [
                            {
                                "type": "paragraph",
                                "text": page_text,
                                "bbox": [0.0, 0.0, 1.0, 1.0],
                                "reading_order": 1,
                                "confidence": 0.8,
                                "children": []
                            }
                        ],
                        "tables": [],
                        "reading_order": [0]
                    }
                    all_graph_pages.append(minimal_page)
                    page_parser_map[p] = "tesseract_ocr"
            except Exception as e:
                _t(f"[ADAPTIVE] Page {p} fallback error: {e}")

    # Determine overall parser string
    unique_parsers = set(page_parser_map.values())
    if not unique_parsers:
        parser_used = "none"
    elif len(unique_parsers) == 1:
        parser_used = unique_parsers.pop()
    else:
        parser_used = "mixed"

    # Persist the full graph as a first-class artifact
    if all_graph_pages:
        # Add overall timings and telemetry
        overall_timings["total_transcription_secs"] = time.perf_counter() - start_time
        overall_timings["recursion_depth"] = recursion_depth
        overall_timings["subdivision_count"] = subdivision_count
        overall_timings["pages_requested"] = len(pages_to_transcribe)
        overall_timings["total_batches_attempted"] = total_batches_attempted
        overall_timings["max_batch_size_attempted"] = max_batch_size_attempted if max_batch_size_attempted > 0 else 0
        overall_timings["min_batch_size_attempted"] = min_batch_size_attempted if min_batch_size_attempted != float('inf') else 0
        overall_timings["batch_history"] = batch_history
        _store_graph(file_path, pages_to_transcribe, all_graph_pages, parser=parser_used, timings=overall_timings)
        _t(f"[ADAPTIVE] Full graph artifact persisted for {len(all_graph_pages)} pages with parser {parser_used}")
    else:
        pass

    return result


def _build_graph_extraction_prompt(pages: List[int], is_whole: bool) -> str:
    """
    Build a lightweight prompt that asks for a compact document representation.
    This reduces response size significantly compared to full bbox/confidence schema.
    The response is still parsed into our internal graph format with defaults.
    """
    page_list = sorted(pages)
    prompt = (
        "You are a document understanding engine. Extract the text and basic structure from the PDF.\n"
        "For each requested page, output a JSON object with the following minimal structure:\n"
        "{\n"
        "  \"pages\": [\n"
        "    {\n"
        "      \"page\": <integer, 1-indexed page number>,\n"
        "      \"text\": \"<full raw text of the page>\",\n"
        "      \"blocks\": [\n"
        "        {\"type\": \"heading|paragraph|list_item|table|equation|figure\", \"text\": \"<content>\"}\n"
        "      ],\n"
        "      \"tables\": [\n"
        "        {\"caption\": \"<caption>\", \"headers\": [\"col1\", ...], \"rows\": [[\"cell1\", ...], ...]}\n"
        "      ]\n"
        "    }\n"
        "  ]\n"
        "}\n"
        "Preserve all text exactly, including equations using LaTeX where appropriate.\n"
        "Do not summarize or skip any content.\n"
        "Only output valid JSON, no other text.\n"
    )
    if not is_whole:
        prompt += f"Only include pages: {page_list}. Return their original page numbers.\n"
    else:
        prompt += f"The document has pages 1..{max(page_list)}. Return all requested pages.\n"
    return prompt


def _transcribe_single_page_fallback(
    file_path: str,
    page_num: int,
    trace_fn: Optional[Callable] = None,
    rate_mgr: Optional[GeminiRateManager] = None,
) -> Optional[str]:
    """Fallback to old image-based single page transcription."""
    def _t(msg: str):
        if trace_fn:
            try:
                trace_fn(msg)
            except Exception:
                pass

    if rate_mgr is None:
        rate_mgr = GeminiRateManager()

    api_key, model = _get_gemini_api_key_and_model()
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    try:
        images = convert_from_path(file_path, first_page=page_num, last_page=page_num, dpi=150)
        if not images:
            _t(f"[FALLBACK] Page {page_num} could not be rendered")
            return None
        img = np.array(images[0])
        decision = rate_mgr.get_decision()
        if not decision.allowed:
            raise RateLimitPauseRequired(
                resume_at=decision.resume_at,
                reason=decision.reason,
                retry_after=decision.retry_after
            )
        slot = rate_mgr.acquire_request_slot()
        if slot is None:
            raise RateLimitPauseRequired(resume_at=time.time() + 30, reason="no_slot_available")
        try:
            _, text = _transcribe_single_page(
                page_idx=page_num-1,
                image=img,
                gemini_endpoint=endpoint,
                rate_mgr=rate_mgr,
                trace_fn=trace_fn,
                max_retries=3
            )
            return text
        finally:
            if slot:
                rate_mgr.release_request_slot(slot)
    except Exception as e:
        _t(f"[FALLBACK] Page {page_num} error: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# VLM Page Transcription (Stateless, uses GeminiRateManager) - kept for fallback
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
    Transcribe a single page using Gemini (image-based). Assumes a slot is already acquired.
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
            _, buffer = cv2.imencode(".png", cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR))
            base64_image = base64.b64encode(buffer).decode("utf-8")
            prompt = (
                "Extract the full document graph from this page. Output JSON with blocks (type, text). "
                "Include tables if present. Response: {\"page\": <number>, \"blocks\": [...], \"tables\": [...]}"
            )
            payload = {
                "contents": [{
                    "parts": [
                        {"text": prompt},
                        {"inlineData": {"mimeType": "image/png", "data": base64_image}}
                    ]
                }],
                "generationConfig": {"temperature": 0.0, "responseMimeType": "application/json"}
            }

            timeout_seconds = getattr(config, "GEMINI_GENERATE_TIMEOUT", 240)
            res = requests.post(gemini_endpoint, headers={"Content-Type": "application/json"}, json=payload, timeout=timeout_seconds)
            if res.status_code == 200:
                data = res.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    _t(f"[VLM] No candidates for page {page_idx+1}")
                    return page_idx, None
                finish_reason = candidates[0].get("finishReason")
                if finish_reason != "STOP":
                    _t(f"[VLM] Page {page_idx+1} finishReason={finish_reason}")
                    if finish_reason in ("SAFETY", "RECITATION"):
                        return page_idx, None
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    else:
                        return page_idx, None
                parts = candidates[0].get("content", {}).get("parts", [])
                if not parts:
                    return page_idx, None
                page_text = parts[0].get("text", "")
                # Try to parse JSON to extract text
                try:
                    parsed = json.loads(page_text)
                    if "blocks" in parsed:
                        text_parts = [b.get("text", "") for b in parsed["blocks"]]
                        page_text = "\n".join(text_parts)
                    elif "text" in parsed:
                        page_text = parsed["text"]
                except:
                    pass
                _t(f"[VLM] Page {page_idx+1} transcribed ({len(page_text)} chars)")
                rate_mgr.register_success()
                return page_idx, page_text
            elif res.status_code in (429, 503) or "quota" in res.text.lower() or "rate limit" in res.text.lower():
                retry_after = 60.0
                try:
                    retry_after = float(res.headers.get("Retry-After", 60.0))
                except:
                    pass
                rate_mgr.register_429(retry_after_header=res.headers.get("Retry-After"))
                raise RateLimitPauseRequired(resume_at=time.time() + retry_after, reason="rate_limit", retry_after=retry_after)
            else:
                if res.status_code in (500, 502, 504):
                    sleep_time = 2 ** attempt
                    _t(f"[VLM] Page {page_idx+1} got HTTP {res.status_code}. Retrying in {sleep_time}s...")
                    time.sleep(sleep_time)
                    continue
                else:
                    _t(f"[VLM] Page {page_idx+1} failed: HTTP {res.status_code}")
                    return page_idx, None
        except RateLimitPauseRequired:
            raise
        except requests.exceptions.Timeout as e:
            last_error = "timeout"
            sleep_time = 2 ** attempt
            _t(f"[VLM] Page {page_idx+1} timeout. Retrying in {sleep_time}s...")
            time.sleep(sleep_time)
            continue
        except requests.exceptions.ConnectionError as e:
            last_error = "connection_error"
            sleep_time = 2 ** attempt
            _t(f"[VLM] Page {page_idx+1} connection error. Retrying in {sleep_time}s...")
            time.sleep(sleep_time)
            continue
        except Exception as e:
            _t(f"[VLM] Page {page_idx+1} error: {e}")
            return page_idx, None
    _t(f"[VLM] Page {page_idx+1} failed after {max_retries} attempts: {last_error}")
    return page_idx, None


# ─────────────────────────────────────────────────────────────────────────────
# Public API: transcribe_pages (kept for backward compatibility)
# ─────────────────────────────────────────────────────────────────────────────
def transcribe_pages(
    file_path: str,
    page_numbers: List[int],
    trace_fn: Optional[Callable] = None,
) -> Dict[int, str]:
    if not page_numbers:
        return {}
    return _execute_adaptive_transcription(file_path, page_numbers, trace_fn, report=None)


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
    def _t(msg: str):
        if trace_fn:
            try:
                trace_fn(msg)
            except Exception:
                pass

    try:
        with open(file_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            total_pages = len(reader.pages)
    except Exception as e:
        raise RuntimeError(f"Failed to read PDF: {e}")

    completed_pages = set(progress_json.get("completed_pages", []) if progress_json else [])
    completed_pages = {p for p in completed_pages if 1 <= p <= total_pages}
    remaining_pages = [p for p in range(1, total_pages + 1) if p not in completed_pages]

    _t(f"[VLM] Legacy wrapper: total={total_pages}, completed={len(completed_pages)}, remaining={len(remaining_pages)}")

    new_transcriptions = {}
    if remaining_pages:
        try:
            report = DocumentPreprocessor(file_path).generate_routing_report(trace_fn)
            new_transcriptions = _execute_adaptive_transcription(file_path, remaining_pages, trace_fn, report=report)
        except RateLimitPauseRequired:
            raise
        except Exception as e:
            _t(f"[VLM] Adaptive transcription failed: {e}. Returning empty.")
            return ""

    if on_page_completed:
        for page_num, text in new_transcriptions.items():
            on_page_completed(page_num, {"text": text, "source": "gemini"})

    page_texts = [text for page_num, text in sorted(new_transcriptions.items())]
    if page_texts:
        return "\n\n<--- PAGE_BREAK --->\n\n".join(page_texts)
    else:
        return ""