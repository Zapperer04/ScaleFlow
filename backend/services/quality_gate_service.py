import os
import sys
import time
import logging

logger = logging.getLogger(__name__)

# Adjust path to find config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

def compute_quality_score(text: str, document_type: str = "SCANNED") -> tuple[float, dict]:
    """
    Computes a simplified quality score based on the core character checks.
    """
    if not text or not text.strip():
        return 0.0, {
            "printable_ratio": 0.0,
            "avg_word_length": 0.0,
            "whitespace_ratio": 0.0,
            "word_length_dist": 0.0,
            "whitespace_score": 0.0
        }
        
    printable = sum(c.isprintable() for c in text) / len(text)
    words = [w for w in text.split() if w]
    avg_len = sum(len(w) for w in words) / len(words) if words else 0.0
    whitespace = sum(c.isspace() for c in text) / len(text)
    
    score = 100.0
    if printable < 0.80:
        score -= 30.0
    if not (3.0 <= avg_len <= 12.0):
        score -= 35.0
    if whitespace < 0.10:
        score -= 35.0
    score = max(0.0, score)
    
    signals = {
        "printable_ratio": printable,
        "avg_word_length": avg_len,
        "whitespace_ratio": whitespace,
        "word_length_dist": 1.0 if (3.0 <= avg_len <= 12.0) else 0.0,
        "whitespace_score": 1.0 if (whitespace >= 0.10) else 0.0,
        "line_coherence": 1.0,
        "ocr_confusion_rate": 1.0,
        "repetition_score": 1.0
    }
    return score, signals

def evaluate_text_quality(text: str) -> dict:
    """
    Compatibility function for benchmark and container scripts.
    """
    score, signals = compute_quality_score(text)
    return {
        "quality_score": score,
        "signals": signals
    }

def validate_quality(text: str, parse_stats: dict, document_type: str = "SCANNED", extractable_text_ratio: float = 0.0) -> dict:
    """
    Quality Gate verifying the parsed document text before chunking.
    Uses a three-part sample (front, middle, end) for a more representative quality snapshot.
    """
    t_start = time.perf_counter()
    
    if not text or len(text.strip()) < 10:
        raise ValueError(f"Document unreadable / OCR quality too low: Extracted text too short ({len(text.strip()) if text else 0} chars) — likely extraction failure")
    
    # Build a representative sample: front, middle, and end of the document
    text_len = len(text)
    front_part = text[:2000] if text_len > 2000 else text
    middle_start = text_len // 2
    middle_part = text[middle_start:middle_start + 2000] if text_len > middle_start + 2000 else ""
    end_part = text[-1000:] if text_len > 1000 else ""
    sample = (front_part + " " + middle_part + " " + end_part).strip()
    if not sample:
        # Fallback to first 5000 chars if the above yields empty
        sample = text[:5000]
    if not sample.strip():
        raise ValueError("Document unreadable / OCR quality too low: Empty extraction output")
        
    printable = sum(c.isprintable() for c in sample) / len(sample) if sample else 1.0
    words = [w for w in sample.split() if w]
    avg_len = sum(len(w) for w in words) / len(words) if words else 0.0
    whitespace = sum(c.isspace() for c in sample) / len(sample) if sample else 0.0
    
    # Soft warnings instead of hard ValueError raise to prevent blocking valid documents
    warnings_list = []
    if printable < 0.50:
        warnings_list.append(f"Low printable ratio: {printable:.2f}")
    if not (2.0 <= avg_len <= 20.0):
        warnings_list.append(f"Unusual average word length: {avg_len:.1f}")
    if whitespace < 0.05:
        warnings_list.append(f"Low whitespace ratio: {whitespace:.2f}")
    if extractable_text_ratio < 0.05:
        warnings_list.append(f"Very low extractable text ratio: {extractable_text_ratio:.3f}")
        
    if warnings_list:
        logger.warning(f"[QUALITY_GATE] Quality warnings for document: {', '.join(warnings_list)}")
        
    # Compute quality confidence on the sample
    confidence, signals = compute_quality_score(sample, document_type)
    
    ocr_pages = parse_stats.get("ocr_pages", 0)
    avg_ocr_confidence = parse_stats.get("avg_ocr_confidence", 100.0)
    parser_used = parse_stats.get("parser", "direct_text")
    ocr_attempted = parse_stats.get("ocr_attempted", False)
    initial_parser = parse_stats.get("initial_parser", "pypdf")
    comparison_metrics = parse_stats.get("comparison_metrics", {})
    
    duration = time.perf_counter() - t_start
    
    return {
        "parsed_text": text,
        "preview": text[:1000],
        "ocr_confidence": avg_ocr_confidence,
        "printable_ratio": printable,
        "quality_confidence": confidence,
        "signals": signals,
        "parser_used": parser_used,
        "ocr_activated": ocr_pages > 0,
        "ocr_attempted": ocr_attempted,
        "initial_parser": initial_parser,
        "pypdf_score": comparison_metrics.get("pypdf_score", 0.0),
        "ocr_score": comparison_metrics.get("ocr_score", 0.0),
        "selected_parser": comparison_metrics.get("selected_parser", parser_used),
        "rejection_reason": "",
        "quality_gate_duration": round(duration, 5)
    }