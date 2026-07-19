import pytest
from backend.infrastructure.storage.qdrant_store import QdrantStore
from backend.infrastructure.storage.vector_store import VectorPoint, VectorQueryFilter

def test_qdrant_store_basic_operations():
    store = QdrantStore()
    
    # Verify health
    h = store.health()
    assert h["status"] == "healthy"
    
    collection = "test_collection"
    
    # 1. Upsert points
    points = [
        VectorPoint(
            id="93a21644-8d48-43e8-9bc9-8e7c10b777a8",
            vector=[1.0] + [0.0] * 767,
            payload={"pipeline_id": 123, "chunk_text": "Sample text one"}
        ),
        VectorPoint(
            id="a6331a61-9c60-4428-a53c-a9c1186711a1",
            vector=[0.0] + [1.0] * 767,
            payload={"pipeline_id": 456, "chunk_text": "Sample text two"}
        )
    ]
    store.upsert(collection, points)
    
    # 2. Query similar
    res = store.query(collection, [1.0] + [0.0] * 767, limit=1)
    assert len(res) == 1
    assert res[0]["chunk_text"] == "Sample text one"
    
    # 3. Query with filter
    filter_dto = VectorQueryFilter(conditions={"pipeline_id": 456})
    res_filtered = store.query(collection, [0.0] + [1.0] * 767, limit=5, filter=filter_dto)
    assert len(res_filtered) == 1
    assert res_filtered[0]["chunk_text"] == "Sample text two"
    
    # 4. Batch query
    batch_res = store.batch_query(collection, [[1.0] + [0.0] * 767, [0.0] + [1.0] * 767], limit=1)
    assert len(batch_res) == 2
    assert batch_res[0][0]["chunk_text"] == "Sample text one"
    assert batch_res[1][0]["chunk_text"] == "Sample text two"
    
    # 5. Delete points
    store.delete(collection, ["93a21644-8d48-43e8-9bc9-8e7c10b777a8"])
    res_after_del = store.query(collection, [1.0] + [0.0] * 767, limit=5)
    # Point with ID "1" is deleted, only "2" remains
    assert all(r.get("chunk_text") != "Sample text one" for r in res_after_del)

