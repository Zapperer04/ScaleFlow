import pytest
from backend.query_router import QueryRouter

def test_query_router_table():
    router = QueryRouter()
    
    res = router.route_query("Extract table of results comparing parameters")
    assert res["intent"] == "table_lookup"
    assert "graph" in res["retrieval_plan"]
    assert res["confidence"] >= 0.9

def test_query_router_multi_hop():
    router = QueryRouter()
    
    res = router.route_query("How does scheduling relate to tasks execution?")
    assert res["intent"] == "multi-hop"
    assert "graph" in res["retrieval_plan"]

def test_query_router_hybrid():
    router = QueryRouter()
    
    res = router.route_query("scheduling details list query options")
    assert res["intent"] == "hybrid"
    assert len(res["reasoning"]) > 0
