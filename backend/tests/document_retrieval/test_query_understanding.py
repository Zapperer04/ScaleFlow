import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.document_retrieval.query_understanding import QueryAnalyzer, QueryUnderstanding

def test_query_analyzer_parsing():
    analyzer = QueryAnalyzer()
    
    # Test table query
    qu_table = analyzer.analyze("Compare row values in Table 1")
    assert qu_table.table_probability > 0.5
    assert "table" in qu_table.keywords
    
    # Test spatial layout query
    qu_spatial = analyzer.analyze("What is at the bottom right header?")
    assert "bottom" in qu_spatial.spatial_constraints
    assert "right" in qu_spatial.spatial_constraints
    
    # Test complexity and keywords
    qu_complex = analyzer.analyze("Explain relationship between authorization and authentication")
    assert qu_complex.graph_probability > 0.5
    assert qu_complex.multi_hop_probability > 0.5
    assert len(qu_complex.keywords) > 2
