import re
import os
from dataclasses import dataclass, field
from typing import List, Dict, Any

try:
    from services.embedding_service import embed_text
    EMBED_AVAILABLE = True
except ImportError:
    EMBED_AVAILABLE = False

@dataclass
class QueryUnderstanding:
    query: str
    embedding: List[float] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    intent_distribution: Dict[str, float] = field(default_factory=dict)
    structural_constraints: List[str] = field(default_factory=list)
    spatial_constraints: List[str] = field(default_factory=list)
    complexity_score: float = 1.0
    multi_hop_probability: float = 0.1
    table_probability: float = 0.0
    graph_probability: float = 0.0

class QueryAnalyzer:
    def analyze(self, query: str) -> QueryUnderstanding:
        if not query:
            return QueryUnderstanding(query="")

        # Compute query embedding
        embedding = []
        if EMBED_AVAILABLE:
            try:
                embedding = embed_text(query)
            except Exception:
                pass
        if not embedding:
            embedding = [0.0] * 768

        # Extract keywords
        stopwords = {"what", "where", "when", "which", "about", "above", "under", "these", "those", "their", "there"}
        words = re.findall(r'\b[a-zA-Z]{4,}\b', query.lower())
        keywords = sorted(list(set([w for w in words if w not in stopwords])))

        # Heuristic entity detection (capitalized words)
        entities = re.findall(r'\b[A-Z][a-z]+\b', query)

        # Likelihood probabilities based on keywords/intents
        query_lower = query.lower()
        
        table_keywords = ["table", "chart", "rows", "columns", "data", "statistics"]
        table_probability = 0.9 if any(k in query_lower for k in table_keywords) else 0.1

        graph_keywords = ["how does", "explain", "relationship", "connect", "why", "structure", "hierarchy"]
        graph_probability = 0.8 if any(k in query_lower for k in graph_keywords) else 0.2

        multi_hop_probability = 0.7 if len(keywords) > 5 or "relationship" in query_lower else 0.1

        # Intent distribution
        intents = {
            "factual": 0.5,
            "comparison": 0.8 if "compare" in query_lower or "versus" in query_lower else 0.1,
            "definition": 0.9 if "define" in query_lower or "meaning of" in query_lower else 0.1
        }

        # Spatial constraints
        spatial_constraints = []
        for word in ["top", "bottom", "left", "right", "header", "footer"]:
            if word in query_lower:
                spatial_constraints.append(word)

        return QueryUnderstanding(
            query=query,
            embedding=embedding,
            entities=entities,
            keywords=keywords,
            intent_distribution=intents,
            structural_constraints=[],
            spatial_constraints=spatial_constraints,
            complexity_score=float(len(keywords)) / 2.0,
            multi_hop_probability=multi_hop_probability,
            table_probability=table_probability,
            graph_probability=graph_probability
        )
