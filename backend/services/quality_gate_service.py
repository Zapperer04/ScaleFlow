import os
import re
import sys

# Adjust path to find config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

def evaluate_text_quality(text: str) -> dict:
    if not text or not text.strip():
        return {
            "quality_score": 0.0,
            "printable_ratio": 0.0,
            "dict_word_ratio": 0.0,
            "coherence_score": 0.0,
            "programming_keyword_score": 0.0
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
    
    programming_keywords = {
        "class", "public", "private", "protected", "void", "return", "static", "import", "extends", "implements",
        "function", "def", "interface", "system", "out", "println", "print", "int", "double", "float", "boolean",
        "bool", "string", "char", "catch", "try", "except", "finally", "throw", "throws", "new", "null", "true",
        "false", "if", "else", "for", "while", "do", "switch", "case", "break", "continue", "struct", "include",
        "namespace", "using", "const", "var", "let"
    }
    
    words = re.findall(r'\b[a-zA-Z]{2,15}\b', text.lower())
    total_words = len(words)
    
    keyword_words_count = sum(1 for w in words if w in programming_keywords)
    programming_keyword_score = round((keyword_words_count / total_words) * 100.0, 1) if total_words > 0 else 0.0
    
    all_dict_words = common_english_words.union(programming_keywords)
    dict_words_count = sum(1 for w in words if w in all_dict_words)
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
        
    min_printable = config.MIN_PRINTABLE_RATIO
    min_dict = config.MIN_DICTIONARY_WORD_RATIO
    min_coherence = config.MIN_TEXT_COHERENCE_SCORE

    quality_score = (dict_word_ratio * 0.6 + (coherence_score / 100.0) * 0.4) * 100.0
    
    effective_min_dict = 0.10 if programming_keyword_score > 3.0 else min_dict
    
    if dict_word_ratio < effective_min_dict:
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
        "coherence_score": round(coherence_score, 1),
        "programming_keyword_score": programming_keyword_score
    }

def validate_quality(text: str, parse_stats: dict) -> dict:
    """
    Quality Gate verifying the parsed document text before chunking.
    Consolidates character, dictionary, and coherence metrics, and performs validation decisions.
    
    Parameters
    ----------
    text        : extracted document text
    parse_stats : statistics dictionary from parsing step
    
    Returns
    -------
    Dictionary of calculated quality gate metrics and validation result.
    """
    import time
    t_start = time.perf_counter()

    if not text:
        raise ValueError("Document unreadable / OCR quality too low: Extracted text is empty.")

    metrics = evaluate_text_quality(text)
    
    ocr_pages = parse_stats.get("ocr_pages", 0)
    avg_ocr_confidence = parse_stats.get("avg_ocr_confidence", 100.0)
    parser_used = parse_stats.get("parser", "direct_text")
    
    min_ocr_conf = config.MIN_OCR_CONFIDENCE
    min_printable = config.MIN_PRINTABLE_RATIO
    min_dict = config.MIN_DICTIONARY_WORD_RATIO
    min_coherence = config.MIN_TEXT_COHERENCE_SCORE
    
    programming_keyword_score = metrics["programming_keyword_score"]
    effective_min_dict = 0.10 if programming_keyword_score > 3.0 else min_dict
    
    # Detect handwritten documents (low-confidence OCR coupled with low dictionary ratio)
    if ocr_pages > 0 and avg_ocr_confidence < 85.0 and metrics["dict_word_ratio"] < 0.30:
        # Avoid hardcoding books, assignments, papers, etc.
        err_msg = (
            "Document Type Not Supported\n\n"
            "This document appears to contain handwritten text.\n\n"
            "ScaleFlow currently supports printed and digital documents only.\n"
            "Handwritten documents are not currently supported due to OCR reliability limitations."
        )
        raise ValueError(err_msg)
        
    failed_checks = []
    if ocr_pages > 0 and avg_ocr_confidence < min_ocr_conf:
        failed_checks.append(f"OCR confidence {avg_ocr_confidence:.1f}% is below threshold {min_ocr_conf:.1f}%")
    if metrics["printable_ratio"] < min_printable:
        failed_checks.append(f"Printable character ratio {metrics['printable_ratio']:.2%} is below threshold {min_printable:.2%}")
    if metrics["dict_word_ratio"] < effective_min_dict:
        failed_checks.append(f"Dictionary-word ratio {metrics['dict_word_ratio']:.2%} is below threshold {effective_min_dict:.2%}")
    if metrics["coherence_score"] < min_coherence:
        failed_checks.append(f"Text coherence score {metrics['coherence_score']:.1f} is below threshold {min_coherence:.1f}")
        
    if failed_checks:
        raise ValueError("Document unreadable / OCR quality too low: " + "; ".join(failed_checks))
        
    comparison_metrics = parse_stats.get("comparison_metrics", {})
    ocr_attempted = parse_stats.get("ocr_attempted", False)
    initial_parser = parse_stats.get("initial_parser", "pypdf")

    duration = time.perf_counter() - t_start

    return {
        "parsed_text": text,
        "preview": text[:1000],
        "ocr_confidence": avg_ocr_confidence,
        "printable_ratio": metrics["printable_ratio"],
        "dict_word_ratio": metrics["dict_word_ratio"],
        "coherence_score": metrics["coherence_score"],
        "parser_used": parser_used,
        "ocr_activated": ocr_pages > 0,
        "ocr_attempted": ocr_attempted,
        "initial_parser": initial_parser,
        "pypdf_score": comparison_metrics.get("pypdf_score", 0.0),
        "ocr_score": comparison_metrics.get("ocr_score", 0.0),
        "selected_parser": comparison_metrics.get("selected_parser", parser_used),
        "rejection_reason": comparison_metrics.get("rejection_reason", ""),
        "quality_gate_duration": round(duration, 5)
    }
