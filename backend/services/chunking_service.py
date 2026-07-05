import re
import sys
import os
from typing import List, Dict

# Adjust path to find config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


# Section detection patterns (as requested)
SECTION_PATTERNS = [
    r'^[A-Z][A-Z\s]{2,}$',
    r'^\d+\.\s+[A-Z]',
    r'^#{1,3}\s',
    r'^(Education|Experience|Technical Skills|Skills|Projects|Summary|Objective|References)',
    r'^(Introduction|Methodology|Results|Conclusion|Abstract|References)',
    r'^(Chapter|Section|Part|Phase)\s+\d+'
]


def detect_content_type(text: str) -> str:
    lines = [l for l in text.strip().split('\n') if l.strip()]
    if not lines:
        return 'paragraph'

    # Table: contains | characters in multiple lines
    if sum(1 for l in lines if '|' in l) >= 2:
        return 'table'

    # List: majority of lines start with bullet/number
    bullet_lines = sum(1 for l in lines
                      if l.strip().startswith(('•', '-', '*', '–'))
                      or re.match(r'^\d+[\.\)]\s', l.strip()))
    if bullet_lines / max(len(lines), 1) > 0.5:
        return 'list'

    # Heading: single short line
    if len(lines) == 1 and len(text.strip()) < 100 and len(text.strip().split()) <= 6:
        return 'heading'

    return 'paragraph'


PATENT_SECTION_HEADERS = {
    'abstract', 'field of the invention', 'technical field', 
    'background of the invention', 'background', 'summary of the invention', 'summary',
    'brief description of the drawings', 'description of the drawings',
    'detailed description', 'detailed description of the preferred embodiments', 
    'detailed description of the invention', 'claims', 'what is claimed is', 'description'
}

def _is_patent_text(text: str) -> bool:
    text_lower = text.lower()
    patent_indicators = [
        "united states patent",
        "patent application publication",
        "patent no.",
        "patent number",
        "application number",
        "filing date",
        "ipc classification",
        "cpc classification",
        "patent document",
        "inventor:",
        "inventors:"
    ]
    matches = sum(1 for ind in patent_indicators if ind in text_lower)
    return matches >= 2

def _match_section_header(line: str, page_number: int = 0, is_patent: bool = False) -> bool:
    s = line.strip()
    if not s:
        return False
    
    # Section headers must be reasonably short
    words = s.split()
    if len(s) > 120 or len(words) > 12:
        return False
        
    # If the line ends with a period and has more than 4 words, it's likely a list item or sentence, not a header
    if s.endswith('.') and len(words) > 4:
        return False

    s_lower = s.lower()
    
    # Phase headers should always be headers
    if re.match(r'^Phase\s+\d+', s, re.IGNORECASE) and len(words) <= 10:
        return True
    
    if is_patent:
        # For patents, only allow standard patent sections or standard sections numbered/cleaned
        cleaned_s = re.sub(r'^(?:\d+[\.\)]|\[\d+\])\s*', '', s_lower).strip()
        if cleaned_s in PATENT_SECTION_HEADERS:
            return True
        return False

    # Standard section titles list (exact match or start-match with very few words)
    standard_sections = {
        'introduction', 'methodology', 'results', 'conclusion', 'abstract', 'references',
        'summary', 'objective', 'education', 'experience', 'technical skills', 'skills',
        'projects', 'references', 'motivation', 'problem statement', 'objectives',
        'literature survey', 'system design', 'testing and optimization', 'ml workflow checklist',
        'workflow checklist'
    }

    # If it is an exact or near-exact match of standard sections
    if s_lower in standard_sections or any(s_lower.startswith(sec) and len(words) <= 5 for sec in standard_sections):
        return True

    # On page 1 (typically cover page), do not treat plain all-caps lines as headers
    # unless they are standard section titles or start with numbers/markdown.
    if page_number == 1 and re.match(r'^[A-Z][A-Z\s\&\-\/\,]{2,}$', s):
        # Only allow explicit standard sections or numbers on page 1
        if s_lower not in {'abstract', 'synopsis', 'summary', 'introduction', 'table of contents', 'objectives'}:
            return False

    # Strictly uppercase line (e.g. "PROBLEM STATEMENT") - must not be a name or single short word
    if re.match(r'^[A-Z][A-Z\s\&\-\/\,]{3,}$', s):
        # Filter out common false positives (dates, single letters, names usually have lowercase or are on cover page)
        if len(words) > 1 and not re.search(r'\b(by|at|on|for|the|of|in|and|a|an)\b', s_lower):
            # Check if this might be a name (cover page names are often all caps like KAUSTAV KUMAR)
            # If page_number == 1, we already filtered out non-standard headers. But just in case, or if page_number is not passed correctly:
            if page_number <= 1:
                return False
            return True
        elif len(words) == 1 and s_lower in {'abstract', 'introduction', 'conclusion', 'references', 'summary', 'objective', 'overview', 'background'}:
            return True
    
    for p in SECTION_PATTERNS[1:]:
        if p == r'^\d+\.\s+[A-Z]':
            if re.match(p, s) and len(words) <= 6:
                return True
        else:
            # For general patterns, require them to be short
            limit = 10 if 'Chapter' in p else 6
            if re.match(p, s, re.IGNORECASE) and len(words) <= limit:
                # If page is 1, be very conservative
                if page_number <= 1:
                    return False
                return True
    return False


def _token_count(s: str) -> int:
    # Rough token approximation using whitespace-split words
    return len(s.split())


def _split_sentences(text: str) -> List[str]:
    # naive sentence splitter that preserves punctuation
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]


def _merge_sentences_to_chunks(sentences: List[str], max_tokens: int, overlap_tokens: int) -> List[str]:
    chunks: List[str] = []
    current: List[str] = []
    current_tokens = 0

    for sent in sentences:
        tok = _token_count(sent)
        # If a single sentence exceeds max_tokens, emit it alone (can't split mid-sentence)
        if tok >= max_tokens and current:
            chunks.append(' '.join(current).strip())
            current = []
            current_tokens = 0

        if current_tokens + tok > max_tokens and current:
            chunks.append(' '.join(current).strip())
            # overlap: keep last sentences until overlap_tokens satisfied
            overlap_block: List[str] = []
            overlap_count = 0
            for s in reversed(current):
                s_tok = _token_count(s)
                if overlap_count + s_tok > overlap_tokens and overlap_block:
                    break
                overlap_block.insert(0, s)
                overlap_count += s_tok
            current = list(overlap_block)
            current_tokens = overlap_count

        current.append(sent)
        current_tokens += tok

    if current:
        chunks.append(' '.join(current).strip())

    return chunks


class ChunkList(list):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.active_section = "unknown"
        self.active_parent = None


def chunk_text(text: str, page_number: int = 0, default_section: str = 'unknown', default_parent: str = None) -> List[Dict]:
    """
    Intelligent semantic segmentation: returns list of dicts { 'text': ..., 'metadata': {...} }
    Metadata includes: section, content_type, page_number, token_count, char_count
    """
    if not text:
        return []

    # Configurable parameters with sensible defaults
    MAX_TOKENS = getattr(config, 'CHUNK_MAX_TOKENS', 400)
    OVERLAP_TOKENS = getattr(config, 'CHUNK_OVERLAP_TOKENS', 50)
    MIN_CHARS = getattr(config, 'CHUNK_MIN_CHARS', 50)
    MAX_CHUNKS = getattr(config, 'MAX_CHUNKS', 1500)

    is_patent = _is_patent_text(text)
    default_sec_name = 'Bibliographic Data' if is_patent else default_section

    lines = text.splitlines()

    # Step 1: detect sections by scanning for headers
    sections: List[Dict] = []
    current_section = {'name': default_sec_name, 'lines': []}

    for line in lines:
        if _match_section_header(line, page_number, is_patent):
            # start new section
            if current_section['lines'] or current_section['name'] != default_sec_name:
                sections.append(current_section)
            hdr = line.strip()
            current_section = {'name': hdr, 'lines': []}
        else:
            current_section['lines'].append(line)

    if current_section['lines'] or current_section['name'] != default_sec_name:
        sections.append(current_section)

    # If we didn't detect any sections, treat whole text as one section
    if not sections:
        sections = [{'name': default_sec_name, 'lines': lines}]

    # Propagate empty parent headers context to sub-sections
    propagated_sections = []
    active_parent = default_parent
    for sec in sections:
        sec_name = sec.get('name') or 'unknown'
        sec_text = '\n'.join(sec.get('lines', [])).strip()
        
        # If a section is empty (contains no lines/text) and is a header, it's a parent header (e.g., "Chapter 4")
        if not sec_text and sec_name != 'unknown':
            active_parent = sec_name
            continue
            
        # If active_parent is set, prefix or associate the current section with it
        full_sec_name = sec_name
        if active_parent and sec_name != 'unknown':
            # If the current section is also a top-level header (e.g. Chapter), we reset active_parent
            if re.match(r'^(Chapter|Part|Volume)\s+\d+', sec_name, re.IGNORECASE):
                active_parent = None
                full_sec_name = sec_name
            else:
                full_sec_name = f"{active_parent} > {sec_name}"
            
        propagated_sections.append({
            'name': full_sec_name,
            'lines': sec.get('lines', [])
        })
    sections = propagated_sections

    segments: List[Dict] = []
    for sec_idx, sec in enumerate(sections):
        sec_name = sec.get('name') or 'unknown'
        sec_text = '\n'.join(sec.get('lines', [])).strip()
        if not sec_text:
            continue

        # For patents, keep bibliographic data and abstract sections unfragmented
        is_bib_or_abstract = is_patent and any(kw in sec_name.lower() for kw in ['bibliographic', 'abstract'])
        if is_bib_or_abstract:
            # Gather all sentences across all paragraphs of the section
            paragraphs = [p.strip() for p in re.split(r'\n{2,}', sec_text) if p.strip()]
            sentences = []
            for p in paragraphs:
                p_sentences = _split_sentences(p)
                sentences.extend(p_sentences)
            
            if sentences:
                merged = _merge_sentences_to_chunks(sentences, MAX_TOKENS, OVERLAP_TOKENS)
                for m_idx, m in enumerate(merged):
                    formatted_text = m
                    if sec_name != 'unknown':
                        formatted_text = f"[Section: {sec_name}] {formatted_text}"
                    
                    segments.append({
                        'text': formatted_text,
                        'metadata': {
                            'section': sec_name,
                            'content_type': 'paragraph',
                            'page_number': page_number,
                            'prev_page_number': page_number - 1 if page_number > 1 else None,
                            'next_page_number': page_number + 1,
                            'parent_chunk_id': f"p{page_number}_s{sec_idx}",
                            'child_chunk_id': f"p{page_number}_s{sec_idx}_c{m_idx}",
                            'token_count': _token_count(formatted_text),
                            'char_count': len(formatted_text)
                        }
                    })
                continue

        # Split section into paragraphs but preserve list blocks and tables
        raw_paragraphs = re.split(r'\n{2,}', sec_text)
        for para_idx, para in enumerate(raw_paragraphs):
            para = para.strip()
            if not para:
                continue

            ctype = detect_content_type(para)
            parent_chunk_id = f"p{page_number}_s{sec_idx}_pa{para_idx}"

            # If list or table, keep item-level granularity
            if ctype == 'list':
                items = [l.strip() for l in para.splitlines() if l.strip()]
                current_list_chunk = []
                current_tokens = 0
                list_chunk_idx = 0
                
                for item in items:
                    item_tokens = _token_count(item)
                    if current_tokens + item_tokens > MAX_TOKENS and current_list_chunk:
                        list_text = "\n".join(current_list_chunk)
                        if sec_name != 'unknown':
                            list_text = f"[Section: {sec_name}] {list_text}"
                        segments.append({
                            'text': list_text,
                            'metadata': {
                                'section': sec_name,
                                'content_type': 'list',
                                'page_number': page_number,
                                'prev_page_number': page_number - 1 if page_number > 1 else None,
                                'next_page_number': page_number + 1,
                                'parent_chunk_id': parent_chunk_id,
                                'child_chunk_id': f"{parent_chunk_id}_l{list_chunk_idx}",
                                'token_count': _token_count(list_text),
                                'char_count': len(list_text)
                            }
                        })
                        list_chunk_idx += 1
                        current_list_chunk = []
                        current_tokens = 0
                    
                    current_list_chunk.append(item)
                    current_tokens += item_tokens
                
                if current_list_chunk:
                    list_text = "\n".join(current_list_chunk)
                    if sec_name != 'unknown':
                        list_text = f"[Section: {sec_name}] {list_text}"
                    segments.append({
                        'text': list_text,
                        'metadata': {
                            'section': sec_name,
                            'content_type': 'list',
                            'page_number': page_number,
                            'prev_page_number': page_number - 1 if page_number > 1 else None,
                            'next_page_number': page_number + 1,
                            'parent_chunk_id': parent_chunk_id,
                            'child_chunk_id': f"{parent_chunk_id}_l{list_chunk_idx}",
                            'token_count': _token_count(list_text),
                            'char_count': len(list_text)
                        }
                    })
                continue

            if ctype == 'table':
                # Keep entire table paragraph as one segment (do not split rows)
                if len(para) >= MIN_CHARS:
                    formatted_text = para
                    if sec_name != 'unknown':
                        formatted_text = f"[Section: {sec_name}] {formatted_text}"

                    segments.append({
                        'text': formatted_text,
                        'metadata': {
                            'section': sec_name,
                            'content_type': 'table',
                            'page_number': page_number,
                            'prev_page_number': page_number - 1 if page_number > 1 else None,
                            'next_page_number': page_number + 1,
                            'parent_chunk_id': parent_chunk_id,
                            'child_chunk_id': f"{parent_chunk_id}_tbl",
                            'token_count': _token_count(formatted_text),
                            'char_count': len(formatted_text)
                        }
                    })
                continue

            # Paragraph or mixed content: split by sentences and then merge into chunks
            sentences = _split_sentences(para)
            if not sentences:
                # fallback: treat as single paragraph
                if len(para) >= MIN_CHARS or ctype == 'heading':
                    formatted_text = para
                    if sec_name != 'unknown':
                        formatted_text = f"[Section: {sec_name}] {formatted_text}"

                    segments.append({
                        'text': formatted_text,
                        'metadata': {
                            'section': sec_name,
                            'content_type': ctype,
                            'page_number': page_number,
                            'prev_page_number': page_number - 1 if page_number > 1 else None,
                            'next_page_number': page_number + 1,
                            'parent_chunk_id': parent_chunk_id,
                            'child_chunk_id': f"{parent_chunk_id}_fb",
                            'token_count': _token_count(formatted_text),
                            'char_count': len(formatted_text)
                        }
                    })
                continue

            merged = _merge_sentences_to_chunks(sentences, MAX_TOKENS, OVERLAP_TOKENS)
            for m_idx, m in enumerate(merged):
                # Keep if it meets the length requirement, is a heading, or is the only content generated from this block
                if len(m) < MIN_CHARS and ctype != 'heading' and len(merged) > 1:
                    continue

                formatted_text = m
                if sec_name != 'unknown':
                    formatted_text = f"[Section: {sec_name}] {formatted_text}"

                segments.append({
                    'text': formatted_text,
                    'metadata': {
                        'section': sec_name,
                        'content_type': detect_content_type(m),
                        'page_number': page_number,
                        'prev_page_number': page_number - 1 if page_number > 1 else None,
                        'next_page_number': page_number + 1,
                        'parent_chunk_id': parent_chunk_id,
                        'child_chunk_id': f"{parent_chunk_id}_c{m_idx}",
                        'token_count': _token_count(formatted_text),
                        'char_count': len(formatted_text)
                    }
                })

    # Determine the final active parent and section
    final_active_parent = active_parent
    final_active_section = default_sec_name
    if sections:
        last_sec = sections[-1]
        last_sec_name = last_sec.get('name') or 'unknown'
        if ' > ' in last_sec_name:
            parts = last_sec_name.split(' > ', 1)
            final_active_parent = parts[0]
            final_active_section = parts[1]
        else:
            final_active_section = last_sec_name

    # final safety cap
    if len(segments) > MAX_CHUNKS:
        raise RuntimeError(f"Chunk explosion detected: Generated {len(segments)} segments (limit is {MAX_CHUNKS}).")

    res = ChunkList(segments)
    res.active_section = final_active_section
    res.active_parent = final_active_parent
    return res


def chunk_text_parent_child(text: str) -> dict:
    """
    Generate parent chunks of target 1200 words [800, 1600]
    and child chunks of target 300 words with 50 words overlap.
    Returns:
        {"parents": {parent_id: text}, "children": [{"text": text, "parent_id": id, "child_id": id}]}
    """
    if not text:
        return {"parents": {}, "children": []}
        
    paragraphs = re.split(r'\n{2,}', text.strip())
    parents = {}
    children = []
    
    current_parent = []
    current_parent_words = 0
    parent_id_counter = 0
    child_id_counter = 0
    
    def process_parent(p_paras, p_id):
        p_text = "\n\n".join(p_paras).strip()
        parents[p_id] = p_text
        
        words = p_text.split()
        target_child_len = 300
        overlap_len = 50
        
        i = 0
        nonlocal child_id_counter
        while i < len(words):
            child_words = words[i:i + target_child_len]
            if not child_words:
                break
            child_text = " ".join(child_words)
            children.append({
                "text": child_text,
                "parent_id": p_id,
                "child_id": f"child_{child_id_counter}"
            })
            child_id_counter += 1
            i += (target_child_len - overlap_len)
            
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        p_words = len(para.split())
        if current_parent_words + p_words > 1200 and current_parent_words >= 800:
            process_parent(current_parent, f"parent_{parent_id_counter}")
            parent_id_counter += 1
            current_parent = [para]
            current_parent_words = p_words
        else:
            current_parent.append(para)
            current_parent_words += p_words
            
    if current_parent:
        process_parent(current_parent, f"parent_{parent_id_counter}")
        
    return {"parents": parents, "children": children}


def chunk_document_graph(document_graph: dict) -> dict:
    """
    Chunks a document graph by extracting texts from nodes and utilizing semantic chunking.
    Returns a dict with {"chunks": list_of_chunks}.
    """
    chunks = []
    if not document_graph:
        return {"chunks": []}

    pages = document_graph.get("pages", [])

    for page in pages:
        page_number = page.get("page_number", 1)
        nodes = page.get("nodes", [])
        nodes = sorted(nodes, key=lambda n: n.get("reading_order", 0))
        
        for node in nodes:
            node_text = node.get("text", "")
            if not node_text.strip():
                continue

            chunks.append({
                "text": node_text,
                "metadata": {
                    "section": node.get("semantic_category") or node.get("section") or "unknown",
                    "semantic_category": node.get("semantic_category") or "unknown",
                    "entity_group": node.get("entity_group") or "unknown",
                    "confidence": node.get("confidence", 1.0),
                    "content_type": node.get("structural_type") or node.get("type", "paragraph"),
                    "node_type": node.get("structural_type") or node.get("type", "paragraph"),
                    "structural_type": node.get("structural_type") or node.get("type", "paragraph"),
                    "page_number": page_number,
                    "chunk_id": node.get("chunk_id") or node.get("node_id"),
                    "token_count": len(node_text.split()),
                    "char_count": len(node_text)
                }
            })
                
    return {"chunks": chunks}
