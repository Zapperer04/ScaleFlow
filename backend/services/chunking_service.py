import re
import sys
import os
import hashlib
import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import defaultdict, deque

# Adjust path to find config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Section detection patterns (legacy for plain text)
# -----------------------------------------------------------------------------
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


def _match_section_header(line: str, page_number: int = 0) -> bool:
    s = line.strip()
    if not s:
        return False
    
    # Section headers must be reasonably short
    words = s.split()
    if len(s) > 120 or len(words) > 12:
        return False
        
    if s.endswith('.') and len(words) > 4:
        return False

    s_lower = s.lower()
    
    if re.match(r'^Phase\s+\d+', s, re.IGNORECASE) and len(words) <= 10:
        return True

    standard_sections = {
        'introduction', 'methodology', 'results', 'conclusion', 'abstract', 'references',
        'summary', 'objective', 'education', 'experience', 'technical skills', 'skills',
        'projects', 'references', 'motivation', 'problem statement', 'objectives',
        'literature survey', 'system design', 'testing and optimization', 'ml workflow checklist',
        'workflow checklist', 'claims', 'description', 'detailed description', 'background'
    }

    if s_lower in standard_sections or any(s_lower.startswith(sec) and len(words) <= 5 for sec in standard_sections):
        return True

    if page_number == 1 and re.match(r'^[A-Z][A-Z\s\&\-\/\,]{2,}$', s):
        if s_lower not in {'abstract', 'synopsis', 'summary', 'introduction', 'table of contents', 'objectives'}:
            return False

    if re.match(r'^[A-Z][A-Z\s\&\-\/\,]{3,}$', s):
        if len(words) > 1 and not re.search(r'\b(by|at|on|for|the|of|in|and|a|an)\b', s_lower):
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
            limit = 10 if 'Chapter' in p else 6
            if re.match(p, s, re.IGNORECASE) and len(words) <= limit:
                if page_number <= 1:
                    return False
                return True
    return False


def _token_count(s: str) -> int:
    return len(s.split())


def _split_sentences(text: str) -> List[str]:
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]


def _merge_sentences_to_chunks(sentences: List[str], max_tokens: int, overlap_tokens: int) -> List[str]:
    chunks: List[str] = []
    current: List[str] = []
    current_tokens = 0

    for sent in sentences:
        tok = _token_count(sent)
        if tok >= max_tokens and current:
            chunks.append(' '.join(current).strip())
            current = []
            current_tokens = 0

        if current_tokens + tok > max_tokens and current:
            chunks.append(' '.join(current).strip())
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


# -----------------------------------------------------------------------------
# Plain‑text chunking (legacy, kept unchanged)
# -----------------------------------------------------------------------------
def chunk_text(text: str, page_number: int = 0, default_section: str = 'unknown', default_parent: str = None) -> List[Dict]:
    """
    Intelligent semantic segmentation for plain text. Returns list of dicts
    { 'text': ..., 'metadata': {...} }.
    """
    if not text:
        return []

    MAX_TOKENS = getattr(config, 'CHUNK_MAX_TOKENS', 400)
    OVERLAP_TOKENS = getattr(config, 'CHUNK_OVERLAP_TOKENS', 50)
    MIN_CHARS = getattr(config, 'CHUNK_MIN_CHARS', 50)
    MAX_CHUNKS = getattr(config, 'MAX_CHUNKS', 1500)

    default_sec_name = default_section
    lines = text.splitlines()

    # Detect sections
    sections: List[Dict] = []
    current_section = {'name': default_sec_name, 'lines': []}

    for line in lines:
        if _match_section_header(line, page_number):
            if current_section['lines'] or current_section['name'] != default_sec_name:
                sections.append(current_section)
            hdr = line.strip()
            current_section = {'name': hdr, 'lines': []}
        else:
            current_section['lines'].append(line)

    if current_section['lines'] or current_section['name'] != default_sec_name:
        sections.append(current_section)

    if not sections:
        sections = [{'name': default_sec_name, 'lines': lines}]

    # Propagate parent context
    propagated_sections = []
    active_parent = default_parent
    for sec in sections:
        sec_name = sec.get('name') or 'unknown'
        sec_text = '\n'.join(sec.get('lines', [])).strip()
        if not sec_text and sec_name != 'unknown':
            active_parent = sec_name
            continue
        full_sec_name = sec_name
        if active_parent and sec_name != 'unknown':
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

        raw_paragraphs = re.split(r'\n{2,}', sec_text)
        for para_idx, para in enumerate(raw_paragraphs):
            para = para.strip()
            if not para:
                continue

            ctype = detect_content_type(para)
            parent_chunk_id = f"p{page_number}_s{sec_idx}_pa{para_idx}"

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

            sentences = _split_sentences(para)
            if not sentences:
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

    if len(segments) > MAX_CHUNKS:
        raise RuntimeError(f"Chunk explosion detected: Generated {len(segments)} segments (limit is {MAX_CHUNKS}).")

    res = ChunkList(segments)
    res.active_section = final_active_section if 'final_active_section' in locals() else 'unknown'
    res.active_parent = final_active_parent if 'final_active_parent' in locals() else None
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


# -----------------------------------------------------------------------------
# GRAPH-NATIVE CHUNKING (ROBUST, PRODUCTION-READY)
# -----------------------------------------------------------------------------

def _get_document_id(graph: Dict) -> str:
    """Extract document ID from graph or generate a stable one."""
    doc_id = graph.get("document_id")
    if not doc_id:
        # Fallback: use a hash of the first few nodes' texts
        pages = graph.get("pages", [])
        texts = []
        for page in pages[:2]:
            for node in page.get("nodes", [])[:5]:
                texts.append(node.get("text", ""))
        if texts:
            doc_id = hashlib.sha256("".join(texts).encode()).hexdigest()[:16]
        else:
            doc_id = "unknown_doc"
    return doc_id


def _build_node_map(pages: List[Dict]) -> Dict[str, Dict]:
    """Map node_id to node object."""
    node_map = {}
    for page in pages:
        page_num = page.get("page_number", 1)
        for node in page.get("nodes", []):
            node_id = node.get("node_id") or node.get("id")
            if node_id:
                node["page_number"] = page_num
                node["reading_order"] = node.get("reading_order", 0)
                # Ensure heading_level has a fallback
                if "heading_level" not in node:
                    # Infer from structural_type or semantic_category
                    if node.get("structural_type") == "heading" or node.get("semantic_category") == "heading":
                        node["heading_level"] = 1  # default, will be refined
                    else:
                        node["heading_level"] = 0
                node_map[node_id] = node
    return node_map


def _build_children_map(nodes: List[Dict]) -> Dict[str, List[str]]:
    """Build mapping from parent node_id to list of child node_ids."""
    children = defaultdict(list)
    for node in nodes:
        parent_id = node.get("parent")
        if parent_id:
            children[parent_id].append(node.get("node_id") or node.get("id"))
    return children


def _infer_heading_level(node: Dict, node_map: Dict) -> int:
    """Infer heading level from parent chain or node attributes."""
    if "heading_level" in node and node["heading_level"] > 0:
        return node["heading_level"]
    # If node is a heading, try to deduce from parent headings
    parent_id = node.get("parent")
    if parent_id and parent_id in node_map:
        parent = node_map[parent_id]
        if parent.get("semantic_category") == "heading" or parent.get("structural_type") == "heading":
            return _infer_heading_level(parent, node_map) + 1
    # Default
    return 1 if (node.get("semantic_category") == "heading" or node.get("structural_type") == "heading") else 0


def _get_heading_path(node: Dict, node_map: Dict) -> List[str]:
    """Return the heading hierarchy path for a node."""
    path = []
    current = node
    while current:
        if current.get("semantic_category") == "heading" or current.get("structural_type") == "heading":
            text = current.get("text", "").strip()
            if text:
                path.append(text)
        parent_id = current.get("parent")
        if parent_id and parent_id in node_map:
            current = node_map[parent_id]
        else:
            break
    path.reverse()
    return path


def _merge_cross_page_paragraphs(nodes: List[Dict]) -> List[Dict]:
    """
    Merge nodes that are logically the same paragraph but split across pages.
    Uses safer criteria: same parent, same structural_type, no heading between,
    and either page boundary with no heading in between.
    """
    if not nodes:
        return []
    merged = []
    i = 0
    while i < len(nodes):
        node = nodes[i]
        if node.get("structural_type") in ("heading", "table", "figure"):
            merged.append(node)
            i += 1
            continue
        # Try to merge with following nodes
        combined_text = node.get("text", "")
        combined_node = dict(node)
        j = i + 1
        while j < len(nodes):
            next_node = nodes[j]
            # Check merge conditions
            if (next_node.get("parent") == node.get("parent") and
                next_node.get("structural_type") == node.get("structural_type") and
                next_node.get("structural_type") not in ("heading", "table", "figure") and
                # no heading between them (check if any heading in between)
                not any(n.get("structural_type") == "heading" for n in nodes[i+1:j]) and
                # page boundary is allowed if same parent and no heading between
                # additional safety: if parser provided a continuation flag, use it
                (node.get("page_number") == next_node.get("page_number") or
                 node.get("continues_next_page") or next_node.get("continues_from_previous"))):
                combined_text += " " + next_node.get("text", "")
                combined_node["page_end"] = next_node.get("page_number", combined_node.get("page_number", 1))
                # Update reading order end
                combined_node["reading_order"] = next_node.get("reading_order", combined_node.get("reading_order", 0))
                j += 1
            else:
                break
        combined_node["text"] = combined_text
        merged.append(combined_node)
        i = j
    return merged


def _collapse_identical_headings(nodes: List[Dict]) -> List[Dict]:
    """Remove consecutive identical heading nodes (keep first)."""
    if not nodes:
        return nodes
    result = []
    prev_heading_text = None
    for node in nodes:
        if node.get("semantic_category") == "heading" or node.get("structural_type") == "heading":
            text = node.get("text", "").strip()
            if text == prev_heading_text:
                continue
            prev_heading_text = text
        else:
            prev_heading_text = None
        result.append(node)
    return result


def _group_into_sections(nodes: List[Dict], node_map: Dict) -> List[Dict]:
    """
    Group nodes into sections based on heading hierarchy.
    Returns list of dicts with keys: 'heading_path', 'heading_nodes', 'content_nodes'.
    Uses inferred heading levels if not present.
    """
    # First, collapse duplicate headings
    nodes = _collapse_identical_headings(nodes)

    sections = []
    current_heading_stack = []  # list of heading nodes
    current_content = []
    current_heading_path = []

    for node in nodes:
        is_heading = node.get("semantic_category") == "heading" or node.get("structural_type") == "heading"
        if is_heading:
            # Determine level
            level = _infer_heading_level(node, node_map)
            # Close current section if it has content
            if current_content:
                sections.append({
                    "heading_path": list(current_heading_path),
                    "heading_nodes": list(current_heading_stack),
                    "content_nodes": current_content
                })
                current_content = []
            # Adjust heading stack: pop headings with level >= current level
            while len(current_heading_stack) >= level and current_heading_stack:
                popped = current_heading_stack.pop()
                # Update path
                current_heading_path = [h.get("text", "").strip() for h in current_heading_stack]
            current_heading_stack.append(node)
            current_heading_path = [h.get("text", "").strip() for h in current_heading_stack]
        else:
            current_content.append(node)

    # Add final section
    if current_content:
        sections.append({
            "heading_path": list(current_heading_path),
            "heading_nodes": list(current_heading_stack),
            "content_nodes": current_content
        })
    # If there are no sections (no headings), create one with all nodes
    if not sections and nodes:
        sections.append({
            "heading_path": [],
            "heading_nodes": [],
            "content_nodes": nodes
        })
    return sections


def _create_chunk_id(doc_id: str, node_ids: List[str]) -> str:
    """Deterministic chunk ID based on document ID and node IDs (stable across page changes)."""
    sorted_ids = sorted(node_ids)
    combined = doc_id + "|" + "|".join(sorted_ids)
    return hashlib.sha256(combined.encode()).hexdigest()[:16]


def _make_metadata(
    doc_id: str,
    chunk_id: str,
    node_ids: List[str],
    heading_path: List[str],
    semantic_category: str,
    structural_type: str,
    page_start: int,
    page_end: int,
    reading_order_start: int,
    reading_order_end: int,
    bbox: Optional[List[float]] = None,
    confidence: Optional[float] = None,
    parent_chunk_id: Optional[str] = None,
    child_chunk_ids: List[str] = None,
    edges: List[Dict] = None,
    additional: Dict = None,
    embed: bool = True
) -> Dict:
    """Build metadata with essential fields only; keep lightweight."""
    meta = {
        "document_id": doc_id,
        "chunk_id": chunk_id,
        "node_ids": node_ids,
        "heading_path": heading_path,
        "section": heading_path[-1] if heading_path else "unknown",
        "semantic_category": semantic_category,
        "structural_type": structural_type,
        "page_start": page_start,
        "page_end": page_end,
        "reading_order_start": reading_order_start,
        "reading_order_end": reading_order_end,
        "confidence": confidence if confidence is not None else 1.0,
        "parent_chunk_id": parent_chunk_id,
        "child_chunk_ids": child_chunk_ids or [],
        "bbox": bbox,
        "source": "graph",
        "parser_version": "2.0",
        "embed": embed  # flag to indicate if this chunk should be embedded
    }
    # Add edges only if present and not too large
    if edges and len(edges) <= 10:
        meta["edges"] = edges
    if additional:
        # Only add small additional fields
        for k, v in additional.items():
            if k in ("table_headers", "caption", "row_count", "col_count", "image_reference", "part_number", "total_parts"):
                meta[k] = v
    return meta


def _split_table(node: Dict, doc_id: str, heading_path: List[str], parent_chunk_id: str, max_rows_per_chunk: int = 50) -> List[Dict]:
    """
    Split a table node into multiple chunks if it has many rows.
    Returns list of chunk dicts (text + metadata) for each table segment.
    """
    rows = node.get("rows") or node.get("table_data") or []
    if not rows:
        return []

    headers = node.get("headers") or []
    caption = node.get("caption") or ""
    total_rows = len(rows)
    node_id = node.get("node_id") or node.get("id")

    if total_rows <= max_rows_per_chunk:
        # No split needed – create metadata using _make_metadata()
        text = node.get("text", "")
        if caption and not text.startswith(caption):
            text = f"{caption}\n{text}"
        meta = _make_metadata(
            doc_id=doc_id,
            chunk_id=_create_chunk_id(doc_id, [node_id] if node_id else []),
            node_ids=[node_id] if node_id else [],
            heading_path=heading_path,
            semantic_category=node.get("semantic_category") or "table",
            structural_type="table",
            page_start=node.get("page_number", 1),
            page_end=node.get("page_number", 1),
            reading_order_start=node.get("reading_order", 0),
            reading_order_end=node.get("reading_order", 0),
            bbox=node.get("bounding_box") or node.get("bbox"),
            confidence=node.get("confidence"),
            parent_chunk_id=parent_chunk_id,
            child_chunk_ids=[],
            edges=node.get("edges", []),
            additional={
                "table_headers": headers[:10],
                "row_count": len(rows),
                "col_count": len(headers) if headers else (len(rows[0]) if rows else 0),
                "caption": caption,
            },
            embed=True
        )
        return [{"text": text, "metadata": meta}]

    # Split rows into chunks
    chunks = []
    total_parts = (total_rows + max_rows_per_chunk - 1) // max_rows_per_chunk
    for i in range(0, total_rows, max_rows_per_chunk):
        chunk_rows = rows[i:i+max_rows_per_chunk]
        part_num = i // max_rows_per_chunk + 1
        # Build text representation
        lines = []
        if caption:
            lines.append(f"Caption: {caption}")
        if headers:
            lines.append("| " + " | ".join(headers) + " |")
        for row in chunk_rows:
            lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
        text = "\n".join(lines)
        chunk_id = _create_chunk_id(doc_id, [f"{node_id}_part_{part_num}"])
        meta = _make_metadata(
            doc_id=doc_id,
            chunk_id=chunk_id,
            node_ids=[node_id],
            heading_path=heading_path,
            semantic_category=node.get("semantic_category") or "table",
            structural_type="table_part",
            page_start=node.get("page_number", 1),
            page_end=node.get("page_number", 1),
            reading_order_start=node.get("reading_order", 0),
            reading_order_end=node.get("reading_order", 0),
            bbox=node.get("bounding_box") or node.get("bbox"),
            confidence=node.get("confidence"),
            parent_chunk_id=parent_chunk_id,
            child_chunk_ids=[],
            edges=node.get("edges", []),
            additional={
                "table_headers": headers[:10],
                "row_count": len(chunk_rows),
                "col_count": len(headers) if headers else (len(chunk_rows[0]) if chunk_rows else 0),
                "caption": caption,
                "part_number": part_num,
                "total_parts": total_parts,
            },
            embed=True
        )
        chunks.append({"text": text, "metadata": meta})
    return chunks


def _process_section(
    section: Dict,
    doc_id: str,
    node_map: Dict,
    children_map: Dict
) -> List[Dict]:
    """
    Process a section to produce child chunks (including table splits).
    Parent hierarchy is stored in metadata (parent_chunk_id) as a separate metadata-only entry.
    Returns list of chunks (each with text and metadata).
    """
    chunks = []
    heading_path = section.get("heading_path", [])
    heading_nodes = section.get("heading_nodes", [])
    content_nodes = section.get("content_nodes", [])

    # Determine section-level metadata for parent (no separate chunk)
    all_node_ids = [n.get("node_id") or n.get("id") for n in heading_nodes + content_nodes if (n.get("node_id") or n.get("id"))]
    if not all_node_ids:
        return chunks

    pages = sorted(set([n.get("page_number", 1) for n in heading_nodes + content_nodes]))
    page_start = pages[0] if pages else 1
    page_end = pages[-1] if pages else 1
    orders = [n.get("reading_order", 0) for n in heading_nodes + content_nodes if n.get("reading_order") is not None]
    order_start = min(orders) if orders else 0
    order_end = max(orders) if orders else 0

    # Create a parent chunk ID (metadata only, no text chunk)
    parent_chunk_id = _create_chunk_id(doc_id, all_node_ids)
    parent_meta = {
        "document_id": doc_id,
        "chunk_id": parent_chunk_id,
        "node_ids": all_node_ids,
        "heading_path": heading_path,
        "section": heading_path[-1] if heading_path else "unknown",
        "semantic_category": "section",
        "structural_type": "section",
        "page_start": page_start,
        "page_end": page_end,
        "reading_order_start": order_start,
        "reading_order_end": order_end,
        "confidence": 1.0,
        "parent_chunk_id": None,
        "child_chunk_ids": [],
        "bbox": None,
        "source": "graph",
        "parser_version": "2.0",
        "embed": False  # do not embed parent chunks
    }

    # Process each content node as a child chunk
    child_ids = []
    for node in content_nodes:
        node_id = node.get("node_id") or node.get("id")
        if not node_id:
            continue
        node_text = node.get("text", "").strip()
        if not node_text:
            continue
        node_type = node.get("structural_type") or node.get("type") or "paragraph"
        node_sem_cat = node.get("semantic_category") or "unknown"

        # Check if it's a table that needs splitting
        if node_type == "table" and node.get("rows") and len(node.get("rows", [])) > 50:
            table_chunks = _split_table(node, doc_id, heading_path, parent_chunk_id)
            for tc in table_chunks:
                child_ids.append(tc["metadata"]["chunk_id"])
                chunks.append(tc)
            continue

        child_chunk_id = _create_chunk_id(doc_id, [node_id])
        child_ids.append(child_chunk_id)

        # Build metadata, keep tables lightweight
        additional = {}
        if node_type == "table":
            # If not split, store headers and counts
            headers = node.get("headers") or []
            rows = node.get("rows") or node.get("table_data") or []
            additional["table_headers"] = headers[:10]
            additional["row_count"] = len(rows)
            additional["col_count"] = len(headers) if headers else (len(rows[0]) if rows else 0)
            if node.get("caption"):
                additional["caption"] = node.get("caption")
        elif node_type == "figure":
            if node.get("caption"):
                additional["caption"] = node.get("caption")
            if node.get("image_reference"):
                additional["image_reference"] = node.get("image_reference")

        meta = _make_metadata(
            doc_id=doc_id,
            chunk_id=child_chunk_id,
            node_ids=[node_id],
            heading_path=heading_path,
            semantic_category=node_sem_cat,
            structural_type=node_type,
            page_start=node.get("page_number", 1),
            page_end=node.get("page_number", 1),
            reading_order_start=node.get("reading_order", 0),
            reading_order_end=node.get("reading_order", 0),
            bbox=node.get("bounding_box") or node.get("bbox"),
            confidence=node.get("confidence"),
            parent_chunk_id=parent_chunk_id,
            child_chunk_ids=[],
            edges=node.get("edges", []),
            additional=additional,
            embed=True
        )
        chunks.append({
            "text": node_text,
            "metadata": meta
        })

    # Update parent's child_chunk_ids and keep it as a metadata-only entry
    if child_ids:
        parent_meta["child_chunk_ids"] = child_ids
        # Add the parent metadata as a separate entry with empty text (embed=False)
        chunks.append({
            "text": "",  # empty text, will be skipped by embedding due to embed=False
            "metadata": parent_meta
        })

    return chunks


def _progressive_degrade(all_chunks: List[Dict], max_chunks: int, all_nodes: List[Dict], doc_id: str) -> List[Dict]:
    """
    Progressive degradation: if chunks exceed limit, merge siblings, drop figures, then fallback to node-level.
    Returns a reduced list of chunks.
    """
    if len(all_chunks) <= max_chunks:
        return all_chunks

    logger.warning(f"Chunk count {len(all_chunks)} exceeds limit {max_chunks}. Attempting progressive degradation.")

    # Step 1: Merge sibling paragraphs with same parent and same structural_type
    # Group by (parent_chunk_id, structural_type)
    grouped = defaultdict(list)
    for c in all_chunks:
        meta = c.get("metadata", {})
        if meta.get("embed") is False:
            # Keep parent metadata as-is (they are already small in number)
            continue
        parent = meta.get("parent_chunk_id")
        stype = meta.get("structural_type")
        if parent and stype in ("paragraph", "list", "text"):
            grouped[(parent, stype)].append(c)

    merged = []
    for (parent, stype), clist in grouped.items():
        if len(clist) <= 1:
            merged.extend(clist)
            continue
        # Merge text
        combined_text = " ".join([c.get("text", "") for c in clist])
        # Use first chunk's metadata as base
        first = clist[0].copy()
        first["text"] = combined_text
        # Update metadata
        meta = first["metadata"].copy()
        # Combine node_ids and sort deterministically
        all_node_ids = []
        for c in clist:
            all_node_ids.extend(c["metadata"].get("node_ids", []))
        all_node_ids = sorted(set(all_node_ids))
        meta["node_ids"] = all_node_ids
        # Generate new chunk_id based on merged node_ids
        meta["chunk_id"] = _create_chunk_id(doc_id, all_node_ids)
        # Update page range
        meta["page_start"] = min(c["metadata"].get("page_start", 1) for c in clist)
        meta["page_end"] = max(c["metadata"].get("page_end", 1) for c in clist)
        # Update reading order
        meta["reading_order_start"] = min(c["metadata"].get("reading_order_start", 0) for c in clist)
        meta["reading_order_end"] = max(c["metadata"].get("reading_order_end", 0) for c in clist)
        # Update token count and char count
        meta["token_count"] = _token_count(combined_text)
        meta["char_count"] = len(combined_text)
        # Confidence: average
        confs = [c["metadata"].get("confidence", 1.0) for c in clist]
        meta["confidence"] = sum(confs) / len(confs)
        # Edges: merge and deduplicate
        edges = []
        for c in clist:
            edges.extend(c["metadata"].get("edges", []))
        # Deduplicate edges by (source, target, type)
        seen = set()
        deduped_edges = []
        for edge in edges:
            if not isinstance(edge, dict):
                continue
            key = (edge.get("source"), edge.get("target"), edge.get("type"))
            if key not in seen:
                seen.add(key)
                deduped_edges.append(edge)
        if deduped_edges:
            meta["edges"] = deduped_edges[:10]
        # Also clear edges if it was set but empty
        elif "edges" in meta:
            del meta["edges"]
        first["metadata"] = meta
        merged.append(first)

    # Add back chunks not grouped (including parent metadata)
    for c in all_chunks:
        meta = c.get("metadata", {})
        if meta.get("embed") is False:
            merged.append(c)
        elif (meta.get("parent_chunk_id"), meta.get("structural_type")) not in grouped:
            merged.append(c)

    if len(merged) <= max_chunks:
        logger.info(f"Progressive degradation step 1: reduced to {len(merged)} chunks.")
        return merged

    # Step 2: Drop figure nodes (they often have captions that may be redundant)
    filtered = [c for c in merged if c.get("metadata", {}).get("structural_type") != "figure"]
    if len(filtered) <= max_chunks and filtered:
        logger.info(f"Progressive degradation step 2: dropped figures, reduced to {len(filtered)} chunks.")
        return filtered

    # Step 3: Fallback to node-level chunks
    logger.warning("Progressive degradation failed. Falling back to node-level chunking.")
    fallback_chunks = []
    for node in all_nodes:
        text = node.get("text", "").strip()
        if not text:
            continue
        node_id = node.get("node_id") or node.get("id")
        chunk_id = _create_chunk_id(doc_id, [node_id] if node_id else [])
        meta = _make_metadata(
            doc_id=doc_id,
            chunk_id=chunk_id,
            node_ids=[node_id] if node_id else [],
            heading_path=[],
            semantic_category=node.get("semantic_category") or "unknown",
            structural_type=node.get("structural_type") or "paragraph",
            page_start=node.get("page_number", 1),
            page_end=node.get("page_number", 1),
            reading_order_start=node.get("reading_order", 0),
            reading_order_end=node.get("reading_order", 0),
            bbox=node.get("bounding_box") or node.get("bbox"),
            confidence=node.get("confidence")
        )
        fallback_chunks.append({"text": text, "metadata": meta})
    return fallback_chunks


def chunk_document_graph(document_graph: dict) -> dict:
    """
    Graph-native semantic chunking. Returns a dict with 'chunks' key containing list of chunk dicts.
    Each chunk has 'text' and 'metadata' (rich but lightweight).
    Preserves compatibility with existing pipeline.
    """
    if not document_graph:
        return {"chunks": []}

    pages = document_graph.get("pages", [])
    if not pages:
        return {"chunks": []}

    doc_id = _get_document_id(document_graph)

    # Build node map and flatten nodes with page info
    node_map = _build_node_map(pages)
    all_nodes = list(node_map.values())

    if not all_nodes:
        return {"chunks": []}

    # Build children map for relationships
    children_map = _build_children_map(all_nodes)

    # Sort by page and reading order
    all_nodes.sort(key=lambda n: (n.get("page_number", 1), n.get("reading_order", 0)))

    # Merge cross-page paragraphs
    merged_nodes = _merge_cross_page_paragraphs(all_nodes)

    # Group into sections using heading hierarchy
    sections = _group_into_sections(merged_nodes, node_map)

    # Process each section to generate chunks
    all_chunks = []
    for section in sections:
        section_chunks = _process_section(section, doc_id, node_map, children_map)
        all_chunks.extend(section_chunks)

    # Fallback: if still no chunks (e.g., no headings, no content), create node-level chunks
    if not all_chunks:
        for node in all_nodes:
            text = node.get("text", "").strip()
            if not text:
                continue
            node_id = node.get("node_id") or node.get("id")
            chunk_id = _create_chunk_id(doc_id, [node_id] if node_id else [])
            meta = _make_metadata(
                doc_id=doc_id,
                chunk_id=chunk_id,
                node_ids=[node_id] if node_id else [],
                heading_path=[],
                semantic_category=node.get("semantic_category") or "unknown",
                structural_type=node.get("structural_type") or "paragraph",
                page_start=node.get("page_number", 1),
                page_end=node.get("page_number", 1),
                reading_order_start=node.get("reading_order", 0),
                reading_order_end=node.get("reading_order", 0),
                bbox=node.get("bounding_box") or node.get("bbox"),
                confidence=node.get("confidence"),
                parent_chunk_id=None,
                child_chunk_ids=[]
            )
            all_chunks.append({"text": text, "metadata": meta})

    # Limit chunks using progressive degradation
    MAX_GRAPH_CHUNKS = getattr(config, 'MAX_GRAPH_CHUNKS', 5000)
    if len(all_chunks) > MAX_GRAPH_CHUNKS:
        all_chunks = _progressive_degrade(all_chunks, MAX_GRAPH_CHUNKS, all_nodes, doc_id)

    # Final filter: keep chunks that have text OR are structural metadata (embed=False)
    all_chunks = [c for c in all_chunks if c.get("text", "").strip() or c.get("metadata", {}).get("embed") is False]

    # Ensure that for embedding chunks, we set the text properly and avoid empty texts
    for c in all_chunks:
        if "chunk_id" not in c["metadata"]:
            c["metadata"]["chunk_id"] = _create_chunk_id(doc_id, c["metadata"].get("node_ids", []))

    # Ensure parent metadata chunks have embed=False
    for c in all_chunks:
        if not c.get("text", "").strip() and c.get("metadata", {}).get("embed") is not False:
            c["metadata"]["embed"] = False

    return {"chunks": all_chunks}