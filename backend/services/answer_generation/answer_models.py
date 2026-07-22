from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class Citation:
    index: int
    chunk_id: str
    graph_node_ids: List[str]
    page_numbers: List[int]
    source_text: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class VerificationResult:
    is_valid: bool
    unsupported_claims: List[str] = field(default_factory=list)
    contradictions: List[str] = field(default_factory=list)
    missing_citations: List[str] = field(default_factory=list)
    verification_score: float = 1.0

@dataclass
class AnswerConfidence:
    overall_score: float
    retrieval_confidence: float
    generation_confidence: float
    citation_coverage: float
    verification_score: float
    confidence_breakdown: Dict[str, float] = field(default_factory=dict)

@dataclass
class GenerationMetrics:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    generation_time: float = 0.0
    verification_time: float = 0.0
    llm_cost: float = 0.0
    citation_count: int = 0
    hallucination_rate: float = 0.0
    retry_count: int = 0
    provider: str = "unknown"
    model: str = "unknown"

@dataclass
class AnswerResult:
    text: str
    citations: List[Citation] = field(default_factory=list)
    verification: VerificationResult = field(default_factory=lambda: VerificationResult(is_valid=True))
    confidence: AnswerConfidence = field(default_factory=lambda: AnswerConfidence(1.0, 1.0, 1.0, 1.0, 1.0))
    metrics: GenerationMetrics = field(default_factory=GenerationMetrics)
    metadata: Dict[str, Any] = field(default_factory=dict)
