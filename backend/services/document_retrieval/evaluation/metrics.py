import math
from typing import List, Set, Dict, Any

class MetricsCalculator:
    @staticmethod
    def compute_recall(retrieved: List[str], expected: List[str], k: int) -> float:
        if not expected:
            return 0.0
        retrieved_k = retrieved[:k]
        intersect = set(retrieved_k).intersection(set(expected))
        return len(intersect) / len(expected)

    @staticmethod
    def compute_precision(retrieved: List[str], expected: List[str], k: int) -> float:
        if not retrieved:
            return 0.0
        retrieved_k = retrieved[:k]
        intersect = set(retrieved_k).intersection(set(expected))
        return len(intersect) / len(retrieved_k)

    @staticmethod
    def compute_mrr(retrieved: List[str], expected: List[str]) -> float:
        if not expected:
            return 0.0
        for idx, item in enumerate(retrieved):
            if item in expected:
                return 1.0 / (idx + 1)
        return 0.0

    @staticmethod
    def compute_ndcg(retrieved: List[str], expected: List[str], k: int) -> float:
        if not expected:
            return 0.0
        retrieved_k = retrieved[:k]
        dcg = 0.0
        for idx, item in enumerate(retrieved_k):
            if item in expected:
                dcg += 1.0 / math.log2(idx + 2)
        idcg = sum(1.0 / math.log2(i + 2) for i in range(min(len(expected), k)))
        return dcg / idcg if idcg > 0 else 0.0

    @staticmethod
    def compute_coverage(retrieved: List[str], expected: List[str]) -> float:
        if not expected:
            return 1.0
        intersect = set(retrieved).intersection(set(expected))
        return len(intersect) / len(expected)

    def calculate_all(self, retrieved_chunks: List[str], expected_chunks: List[str],
                      retrieved_nodes: List[str], expected_nodes: List[str],
                      retrieved_entities: List[str], expected_entities: List[str],
                      retrieved_tables: List[str], expected_tables: List[str]) -> Dict[str, float]:
        return {
            "recall_1": self.compute_recall(retrieved_chunks, expected_chunks, 1),
            "recall_3": self.compute_recall(retrieved_chunks, expected_chunks, 3),
            "recall_5": self.compute_recall(retrieved_chunks, expected_chunks, 5),
            "recall_10": self.compute_recall(retrieved_chunks, expected_chunks, 10),
            "precision_1": self.compute_precision(retrieved_chunks, expected_chunks, 1),
            "precision_5": self.compute_precision(retrieved_chunks, expected_chunks, 5),
            "mrr": self.compute_mrr(retrieved_chunks, expected_chunks),
            "ndcg_5": self.compute_ndcg(retrieved_chunks, expected_chunks, 5),
            "graph_coverage": self.compute_coverage(retrieved_nodes, expected_nodes),
            "entity_coverage": self.compute_coverage(retrieved_entities, expected_entities),
            "table_coverage": self.compute_coverage(retrieved_tables, expected_tables),
            "context_recall": self.compute_recall(retrieved_chunks, expected_chunks, 5),
            "context_precision": self.compute_precision(retrieved_chunks, expected_chunks, 5)
        }
