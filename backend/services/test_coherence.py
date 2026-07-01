#!/usr/bin/env python
"""
Test script to verify text coherence scoring distinguishes between:
- Digital PDFs (high coherence, should NOT route to VLM)
- Scanned PDFs (low coherence, should route to VLM)
- Handwritten docs (low coherence, should route to VLM)
"""
import sys
sys.path.insert(0, 'backend/services')

from document_preprocessor import _score_text_coherence

# Test cases
test_cases = [
    # Digital PDF - typical well-formatted text
    ("digital", """
    Chapter 1: Introduction

    This is a sample digital PDF document with proper text extraction.
    The text is well-structured and contains normal word lengths.

    Key features:
    - Proper formatting
    - Standard paragraphs
    - Normal punctuation

    The document flows naturally with clear headings and content.
    """),

    # Scanned PDF - OCR artifact text (even more emphatic)
    ("scanned", """
    T his is & sample 0 scanning 0 f this PDF d0cument.
    The t3xt has n7mber 5 su6stitutions 4nd w6ird ch4rs.
    1t was c0nv3rt3d t0 d1g1tal by 0cr pr0cess1ng.

    P4ge 1:
    Th1s p4ge h4s m4ny r4nd0m subs t1tu t10ns.
    Th3s3 w0rds h4v3 d1g1t5s 1ns1d3 r4nd0mly
    And th4t'5 0 co0mon p4tt3rn 1n 0cr 7ext.
    """),

    # Handwritten-like - irregular text with numbers
    ("handwritten", """
    Ths s a hm handwritten documnt.
    The text s very irr gular and has sm ny letts.
    It ws wrtten by hand and scnasned.
    Ths chaactar by chaactar appraoch is dffrnt.
    This 5a5 m1x3d 3xtract10n with 3xp0rt13nt.
    """),

    # Novel-like - clean digital text
    ("novel", """
    Chapter One

    It was the best of times, it was the worst of times.
    A change was as good as a rest.
    The road of life is long and uncertain.

    The character walked through the forest.
    Birds sang in the trees above.
    The path wound up the mountain side.
    """),

    # Very good digital PDF - should definitely pass
    ("perfect_digital", """
    Professional Document Format

    This is a perfectly formatted digital document with proper typography.
    Regular prose flows smoothly with correct grammar and punctuation.
    Sections and subsections are clearly identified with heading styles.

    Mathematical equations like E = mc² are rendered correctly.
    Tables, charts, and graphs appear properly aligned.
    Quotations use standard formatting with proper punctuation.
    Technical terms maintain consistent capitalization and spelling.
    """),

    # Very poor OCR - should fail badly
    ("poor_ocr", """
    T h i s   i s   a n   e x a m p l e   o f   r e a l l y   b a d   o c r   t e x t.
    T h e   w o r d s   a r e   s e p a r a t e d   w i t h   w e i r d   s p a c i n g.
    S u b s t i t u t i o n s   a r e   v e r y   w i r d   f o r   e x a m p l e:
    "B u d g e t = $" , "F i g u r e  5 . 2 , " ( r o n d   s p a c i n g ).
    P a r a g r a p h s   a r e   c o m p l e t e l y   d i s r u p t e d   a n d   c o n t i n u e.
    """),
]

print("=" * 70)
print("Text Coherence Scoring Test Results")
print("=" * 70)
print(f"{'Document Type':<15} {'Score':<10} {'Expected':<15} {'Status':<10}")
print("-" * 70)

for doc_type, text in test_cases:
    score = _score_text_coherence(text)
    expected = "HIGH (>50)" if doc_type in ["digital", "novel"] else "LOW (<50)"
    status = "PASS" if (score > 50 and doc_type in ["digital", "novel"]) or (score <= 50 and doc_type in ["scanned", "handwritten"]) else "FAIL"
    print(f"{doc_type:<15} {score:<10.1f} {expected:<15} {status:<10}")

print("=" * 70)
print("\nRouting Decision Test:")
print("-" * 70)
for doc_type, text in test_cases:
    score = _score_text_coherence(text)
    route_to_vlm = score < 50.0
    arrow = "->"
    print(f"{doc_type:<15}: Score={score:<6.1f} {arrow} {'VLM' if route_to_vlm else 'DIRECT'}")