import re
import sys
import os

# Adjust path to find config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

def _is_heading(line: str) -> bool:
    stripped = line.strip()
    # Markdown-style headings
    if re.match(r'^#{1,4}\s', stripped):
        return True
    # ALL CAPS lines of moderate length (section titles)
    if (len(stripped) > 4 and len(stripped) < 80
            and stripped == stripped.upper() and stripped.replace(" ", "").isalpha()):
        return True
    # Numbered sections like "1.2 Introduction" or "Chapter 3"
    if re.match(r'^(chapter|section|appendix|part)?\s*\d+[.\d]*\s+\w', stripped, re.IGNORECASE):
        return True
    return False

def _words(s: str) -> int:
    return len(s.split())

def _get_overlap_text(paragraph: str) -> str:
    """
    Extract the end of the paragraph representing approximately CHUNK_OVERLAP_WORDS to CHUNK_OVERLAP_MAX_WORDS,
    preserving sentence boundaries.
    """
    if not paragraph:
        return ""
    sentences = re.split(r'(?<=[.!?])\s+', paragraph)
    if not sentences:
        return ""
    
    current_block = []
    current_words = 0
    overlap_target = config.CHUNK_OVERLAP_WORDS
    overlap_max = config.CHUNK_OVERLAP_MAX_WORDS
    
    for sent in reversed(sentences):
        sent_words = len(sent.split())
        if current_words + sent_words > overlap_max and current_block:
            break
        current_block.insert(0, sent)
        current_words += sent_words
        if current_words >= overlap_target:  # Target CHUNK_OVERLAP_WORDS
            break
            
    res = " ".join(current_block)
    if len(res.split()) > overlap_max:
        res = " ".join(res.split()[-int(overlap_max * 0.75):])
    return res

def chunk_text(text: str) -> list[str]:
    """
    Split text into coherent, retrieval-optimised chunks:
    - Paragraph-aware: never splits a paragraph mid-sentence
    - Heading-aware: detected headings start fresh chunks
    - Target size: configurable CHUNK_TARGET_WORDS
    - Overlap size: configurable CHUNK_OVERLAP_WORDS
    - Min chunk: configurable CHUNK_MIN_WORDS
    - Max chunks: configurable MAX_CHUNKS
    """
    if not text:
        return []
        
    target_words = config.CHUNK_TARGET_WORDS
    min_words = config.CHUNK_MIN_WORDS
    max_chunks = config.MAX_CHUNKS

    # ── step 1: split into paragraphs ────────────────────────────────────────
    raw_paragraphs = re.split(r'\n{2,}', text)
    paragraphs = []
    for p in raw_paragraphs:
        p = p.strip()
        if not p:
            continue
        # Break at headings within a paragraph block
        lines = p.splitlines()
        current_block: list[str] = []
        for line in lines:
            if _is_heading(line) and current_block:
                paragraphs.append(" ".join(current_block).strip())
                current_block = [line]
            else:
                current_block.append(line)
        if current_block:
            paragraphs.append(" ".join(current_block).strip())

    # Split overly large paragraphs into smaller sub-paragraphs (e.g. by sentence)
    split_paragraphs = []
    for para in paragraphs:
        if _words(para) <= target_words:
            split_paragraphs.append(para)
        else:
            sentences = re.split(r'(?<=[.!?])\s+', para)
            current_sent_block: list[str] = []
            current_sent_words = 0
            for sent in sentences:
                sent_words = _words(sent)
                if current_sent_words + sent_words > target_words and current_sent_block:
                    split_paragraphs.append(" ".join(current_sent_block))
                    current_sent_block = []
                    current_sent_words = 0
                current_sent_block.append(sent)
                current_sent_words += sent_words
            if current_sent_block:
                split_paragraphs.append(" ".join(current_sent_block))
    paragraphs = split_paragraphs

    # ── step 2: accumulate paragraphs into chunks ─────────────────────────────
    chunks: list[str] = []
    current_chunk_parts: list[str] = []
    current_word_count = 0
    last_paragraph = ""   # kept for overlap bridge

    for para in paragraphs:
        para_words = _words(para)

        # A heading or the addition of this paragraph would overflow — flush
        if (_is_heading(para) or current_word_count + para_words > target_words) \
                and current_chunk_parts:
            chunk_text_val = "\n\n".join(current_chunk_parts).strip()
            if _words(chunk_text_val) >= min_words:
                chunks.append(chunk_text_val)

            # Overlap: carry last paragraph's end into next chunk
            overlap_text = _get_overlap_text(last_paragraph) if last_paragraph else ""
            current_chunk_parts = [overlap_text] if overlap_text else []
            current_word_count = _words(overlap_text) if current_chunk_parts else 0

        current_chunk_parts.append(para)
        current_word_count += para_words
        last_paragraph = para

    # Flush final chunk
    if current_chunk_parts:
        chunk_text_val = "\n\n".join(current_chunk_parts).strip()
        if _words(chunk_text_val) >= min_words:
            chunks.append(chunk_text_val)

    # Safety net for very short documents:
    if not chunks and text.strip():
        chunks.append(text.strip())

    # ── step 3: resource cap ─────────────────────────────────────────────────
    if len(chunks) > max_chunks:
        raise RuntimeError(f"Chunk explosion detected: Generated {len(chunks)} chunks (limit is {max_chunks}).")

    return chunks
