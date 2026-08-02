import pytest
from backend.citation_builder import CitationBuilder
from backend.context_fusion import FusedContext

def test_citation_builder_explicit_brackets():
    builder = CitationBuilder()
    
    # Setup mock FusedContext
    context = FusedContext()
    context.provenance_map["chunk_doc_1"] = {
        "chunk_id": "chunk_doc_1",
        "text": "ScaleFlow uses Whoosh for indexing document metadata dynamically.",
        "page": 2,
        "bbox": {"ymin": 0.1, "xmin": 0.1, "ymax": 0.2, "xmax": 0.8},
        "section_id": "sec_architecture",
        "graph_node_ids": ["node_arch_1"]
    }

    answer = "ScaleFlow executes lexical indexing using Whoosh [chunk_doc_1]."
    citations = builder.build_citations(answer, context)
    
    assert len(citations) == 1
    cit = citations[0]
    assert cit["chunk_id"] == "chunk_doc_1"
    assert cit["page"] == 2
    assert cit["section"] == "sec_architecture"
    assert cit["graph_node_id"] == "node_arch_1"
    assert cit["bbox"]["ymin"] == 0.1

def test_citation_builder_fuzzy_matching():
    builder = CitationBuilder()
    
    context = FusedContext()
    # Supporting chunk text
    context.supporting_chunks.append({
        "chunk_id": "chunk_doc_2",
        "text": "The Qdrant Vector store contains embedding points mapped to task pipeline outputs.",
        "page": 4,
        "bbox": {"ymin": 0.3, "xmin": 0.3, "ymax": 0.4, "xmax": 0.7},
        "section_id": "sec_qdrant",
        "graph_node_ids": ["node_qdrant_2"]
    })
    # Copy to provenance map
    context.provenance_map["chunk_doc_2"] = context.supporting_chunks[0]

    answer = "The Qdrant Vector store contains embedding points mapped to task pipeline outputs."
    citations = builder.build_citations(answer, context)
    
    assert len(citations) == 1
    cit = citations[0]
    assert cit["chunk_id"] == "chunk_doc_2"
    assert cit["page"] == 4
    assert cit["section"] == "sec_qdrant"
