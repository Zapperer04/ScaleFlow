from typing import List, Dict, Any

class QueryRouter:
    def __init__(self):
        pass

    def route_query(self, query: str) -> Dict[str, Any]:
        query_lower = query.lower()
        reasoning = []
        retrieval_plan = []
        intent = "hybrid"
        confidence = 0.8
        
        # 1. Table Lookup Intent
        if "table" in query_lower or "rows" in query_lower or "columns" in query_lower or "tabular" in query_lower:
            intent = "table_lookup"
            confidence = 0.95
            reasoning.append("contains table-specific vocabulary ('table', 'rows', 'columns')")
            if any(char.isdigit() for char in query_lower):
                reasoning.append("contains numerical entities / constraints")
                confidence = 0.98
            retrieval_plan = ["graph", "semantic", "bm25"]

        # 2. Figure Lookup Intent
        elif "figure" in query_lower or "image" in query_lower or "diagram" in query_lower or "chart" in query_lower or "illustration" in query_lower:
            intent = "figure_lookup"
            confidence = 0.92
            reasoning.append("contains visualization keywords ('figure', 'image', 'diagram')")
            retrieval_plan = ["graph", "semantic"]

        # 3. Comparison Intent
        elif "compare" in query_lower or "difference" in query_lower or "versus" in query_lower or "vs" in query_lower or "contrast" in query_lower:
            intent = "comparison"
            confidence = 0.88
            reasoning.append("contains comparison indicators ('compare', 'versus', 'vs')")
            retrieval_plan = ["semantic", "bm25", "graph"]

        # 4. Definition Intent
        elif "what is" in query_lower or "define" in query_lower or "meaning of" in query_lower or "definition" in query_lower:
            intent = "definition"
            confidence = 0.85
            reasoning.append("matches definition/conceptual phrasing patterns")
            retrieval_plan = ["semantic", "bm25"]

        # 5. Multi-Hop / Graph Traversal Intent
        elif "how does" in query_lower or "relationship" in query_lower or "connected" in query_lower or "link" in query_lower or "leads to" in query_lower:
            intent = "multi-hop"
            confidence = 0.87
            reasoning.append("indicates multi-hop structural traversal request")
            retrieval_plan = ["graph", "semantic", "bm25"]

        # Default Hybrid Intent
        else:
            intent = "hybrid"
            confidence = 0.75
            reasoning.append("no strong single-intent features detected; applying standard hybrid search")
            retrieval_plan = ["semantic", "bm25", "graph"]

        return {
            "intent": intent,
            "confidence": confidence,
            "reasoning": reasoning,
            "retrieval_plan": retrieval_plan
        }
