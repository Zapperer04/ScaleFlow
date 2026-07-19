from typing import Sequence, List, Optional, Dict, Any
from backend.infrastructure.storage.vector_store import BaseVectorStore, VectorPoint, VectorQueryFilter
from backend.services.vector_store import get_client, ensure_collection
import config

class QdrantStore(BaseVectorStore):
    """Qdrant wrapper implementing BaseVectorStore."""

    def __init__(self):
        pass

    def upsert(self, collection_name: str, points: Sequence[VectorPoint]) -> None:
        from qdrant_client.http import models as qmodels
        client = get_client()
        ensure_collection(collection_name, config.EMBEDDING_DIMENSION)
        q_points = [
            qmodels.PointStruct(
                id=p.id,
                vector=p.vector,
                payload=p.payload
            ) for p in points
        ]
        client.upsert(collection_name=collection_name, points=q_points, wait=True)

    def delete(self, collection_name: str, point_ids: List[str]) -> None:
        from qdrant_client.http import models as qmodels
        client = get_client()
        ensure_collection(collection_name, config.EMBEDDING_DIMENSION)
        client.delete(
            collection_name=collection_name,
            points_selector=qmodels.PointIdsList(points=point_ids)
        )

    def query(
        self,
        collection_name: str,
        vector: List[float],
        limit: int = 5,
        filter: Optional[VectorQueryFilter] = None
    ) -> List[Dict[str, Any]]:
        from qdrant_client.http import models as qmodels
        client = get_client()
        ensure_collection(collection_name, config.EMBEDDING_DIMENSION)
        
        q_filter = None
        if filter and filter.conditions:
            conditions = []
            for key, val in filter.conditions.items():
                if val is not None:
                    val_to_match = val
                    if key in ("pipeline_id", "file_id"):
                        try:
                            val_to_match = int(val)
                        except (ValueError, TypeError):
                            pass
                    conditions.append(
                        qmodels.FieldCondition(
                            key=key,
                            match=qmodels.MatchValue(value=val_to_match)
                        )
                    )
            if conditions:
                q_filter = qmodels.Filter(must=conditions)

        search_result = client.search(
            collection_name=collection_name,
            query_vector=vector,
            limit=limit,
            query_filter=q_filter
        )
        
        results = []
        for hit in search_result:
            res = dict(hit.payload or {})
            res["score"] = round(hit.score, 4)
            results.append(res)
        return results

    def batch_query(
        self,
        collection_name: str,
        vectors: List[List[float]],
        limit: int = 5
    ) -> List[List[Dict[str, Any]]]:
        from qdrant_client.http import models as qmodels
        client = get_client()
        ensure_collection(collection_name, config.EMBEDDING_DIMENSION)
        
        requests = [
            qmodels.SearchRequest(
                vector=v,
                limit=limit,
                with_payload=True
            ) for v in vectors
        ]
        
        batch_results = client.search_batch(
            collection_name=collection_name,
            requests=requests
        )
        
        overall_results = []
        for search_result in batch_results:
            results = []
            for hit in search_result:
                res = dict(hit.payload or {})
                res["score"] = round(hit.score, 4)
                results.append(res)
            overall_results.append(results)
        return overall_results

    def health(self) -> dict:
        try:
            client = get_client()
            client.get_collections()
            return {"status": "healthy", "type": "qdrant"}
        except Exception as e:
            return {"status": "unhealthy", "type": "qdrant", "error": str(e)}
