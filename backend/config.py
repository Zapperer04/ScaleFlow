import os

def load_env():
    # Attempt to load from various potential locations of .env
    for path in ['.env', 'backend/.env', '../backend/.env', '../../.env']:
        try:
            with open(path) as f:
                for line in f:
                    if line.strip() and not line.startswith('#'):
                        key, val = line.strip().split('=', 1)
                        os.environ.setdefault(key.strip(), val.strip())
                break
        except FileNotFoundError:
            pass

load_env()

# CENTRAL CONFIGURATION FOR SCALEFLOW

# 1. Chunking Config
CHUNK_TARGET_WORDS = int(os.getenv("CHUNK_TARGET_WORDS", "500"))
CHUNK_MIN_WORDS = int(os.getenv("CHUNK_MIN_WORDS", "40"))
MAX_CHUNKS = int(os.getenv("MAX_CHUNKS", "1500"))
CHUNK_OVERLAP_WORDS = int(os.getenv("CHUNK_OVERLAP_WORDS", "55"))
CHUNK_OVERLAP_MAX_WORDS = int(os.getenv("CHUNK_OVERLAP_MAX_WORDS", "100"))
MAX_CHARACTER_LIMIT = int(os.getenv("MAX_CHARACTER_LIMIT", "2000000"))

# 2. Quality / Coherence Thresholds
MIN_PRINTABLE_RATIO = float(os.getenv("MIN_PRINTABLE_RATIO", "0.85"))
MIN_DICTIONARY_WORD_RATIO = float(os.getenv("MIN_DICTIONARY_WORD_RATIO", "0.20"))
MIN_TEXT_COHERENCE_SCORE = float(os.getenv("MIN_TEXT_COHERENCE_SCORE", "60.0"))

# 3. OCR / Parsing Config
MIN_OCR_CONFIDENCE = float(os.getenv("MIN_OCR_CONFIDENCE", "70.0"))
PDF_LOW_TEXT_CHARS = int(os.getenv("PDF_LOW_TEXT_CHARS", "20"))
PDF_MAX_PAGES = int(os.getenv("PDF_MAX_PAGES", "600"))
PDF_MEMORY_LIMIT_MB = int(os.getenv("PDF_MEMORY_LIMIT_MB", "1500"))
PDF_PARSE_TIMEOUT_S = int(os.getenv("PDF_PARSE_TIMEOUT_S", "1800"))

# 4. Retrieval Config
DEFAULT_RETRIEVAL_TOP_K = int(os.getenv("DEFAULT_RETRIEVAL_TOP_K", "5"))
MIN_RETRIEVAL_SCORE = float(os.getenv("MIN_RETRIEVAL_SCORE", "0.3"))

# 5. Embedding Model Config
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-base-en-v1.5")
EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "768"))
EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "64"))
EMBEDDING_QUANTIZATION = os.getenv("EMBEDDING_QUANTIZATION", "False").lower() in ("true", "1", "yes")
EMBEDDING_NUM_THREADS = int(os.getenv("EMBEDDING_NUM_THREADS", "4"))

# 6. Parser Priorities Config
PARSER_PRIORITIES = [p.strip() for p in os.getenv("PARSER_PRIORITIES", "pypdf,pdfplumber,ocr").lower().split(",") if p.strip()]

# 7. Backpressure Config
BACKPRESSURE_ENABLED = os.getenv("BACKPRESSURE_ENABLED", "True").lower() in ("true", "1", "yes")
BACKPRESSURE_MAX_BACKLOG = int(os.getenv("BACKPRESSURE_MAX_BACKLOG", "50"))
BACKPRESSURE_CRITICAL_WAIT = float(os.getenv("BACKPRESSURE_CRITICAL_WAIT", "30.0"))
BACKPRESSURE_SATURATED_UTILIZATION = float(os.getenv("BACKPRESSURE_SATURATED_UTILIZATION", "90.0"))
BACKPRESSURE_LOW_PRIORITY_THROTTLE = int(os.getenv("BACKPRESSURE_LOW_PRIORITY_THROTTLE", "5"))
BACKPRESSURE_AGING_THRESHOLD_SECONDS = int(os.getenv("BACKPRESSURE_AGING_THRESHOLD_SECONDS", "60"))
BACKPRESSURE_OVERLOAD_POLICY = os.getenv("BACKPRESSURE_OVERLOAD_POLICY", "defer")

# 8. Document Preprocessing Config
# Thresholds for quality evaluation (0–100 scale, higher = better quality)
PREPROCESS_BLUR_MIN          = float(os.getenv("PREPROCESS_BLUR_MIN", "40.0"))
PREPROCESS_CONTRAST_MIN      = float(os.getenv("PREPROCESS_CONTRAST_MIN", "35.0"))
PREPROCESS_DPI_MIN           = float(os.getenv("PREPROCESS_DPI_MIN", "150.0"))
PREPROCESS_SKEW_MAX_DEG      = float(os.getenv("PREPROCESS_SKEW_MAX_DEG", "2.0"))
PREPROCESS_NOISE_MIN         = float(os.getenv("PREPROCESS_NOISE_MIN", "40.0"))

# Handwriting detection
PREPROCESS_HW_SCORE_MIN      = float(os.getenv("PREPROCESS_HW_SCORE_MIN", "0.70"))
PREPROCESS_HW_TEXT_RATIO_MAX = float(os.getenv("PREPROCESS_HW_TEXT_RATIO_MAX", "0.10"))
# Opt-in: set to True to hard-reject heavily handwritten documents.
# Default is False — handwriting is a warning flag only.
# The pipeline is domain-agnostic; handwritten inputs are valid in many domains.
PREPROCESS_REJECT_HANDWRITTEN = os.getenv("PREPROCESS_REJECT_HANDWRITTEN", "False").lower() in ("true", "1", "yes")

# Sampling and enhancement
PREPROCESS_SAMPLE_PAGES       = int(os.getenv("PREPROCESS_SAMPLE_PAGES", "5"))
PREPROCESS_TARGET_DPI         = int(os.getenv("PREPROCESS_TARGET_DPI", "300"))
# Cap on pages that receive enhancement. Pages beyond this are appended unenhanced.
# Prevents worker timeouts on large scanned documents.
PREPROCESS_MAX_ENHANCE_PAGES  = int(os.getenv("MAX_ENHANCED_PAGE_COUNT", "25"))
# Feature flags for expensive image operations
PREPROCESS_ENABLE_DENOISE     = os.getenv("PREPROCESS_ENABLE_DENOISE", "False").lower() in ("true", "1", "yes")
PREPROCESS_ENABLE_SHARPEN     = os.getenv("PREPROCESS_ENABLE_SHARPEN", "False").lower() in ("true", "1", "yes")

# Optional: absolute path to the directory containing Poppler binaries (pdftoppm, pdfinfo).
# Leave empty to use the system PATH. Required on Windows when Poppler was installed
# but its bin directory is not yet on PATH (e.g. after a fresh winget install).
PREPROCESS_POPPLER_PATH       = os.getenv("PREPROCESS_POPPLER_PATH", "")

