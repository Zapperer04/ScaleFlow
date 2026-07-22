from typing import List, Dict, Any, Optional
from engine.answer_generation.orchestrator import AnswerOrchestrator
from backend.platform.services.inference_gateway import InferenceGateway
from backend.platform.cache.answer_cache import AnswerCache

class GenerationService:
    def __init__(self, gateway: InferenceGateway):
        self.orchestrator = AnswerOrchestrator()
        self.gateway = gateway
        self.cache = AnswerCache()
        
        # Override the engine generator's generate_answer call to pass through our InferenceGateway
        self.orchestrator.generator.generate_answer = self._gateway_generate_adapter

    def _gateway_generate_adapter(self, prompt: str) -> Dict[str, Any]:
        """
        Adapts engine generator calls to run through our platform inference gateway.
        """
        # Call the platform inference gateway
        res = self.gateway.generate(prompt)
        return {
            "text": res["text"],
            "prompt_tokens": res["prompt_tokens"],
            "completion_tokens": res["completion_tokens"],
            "provider": res["provider"],
            "model": res["model"]
        }

    def generate_answer(
        self,
        query: str,
        query_understanding: Any,
        candidates: List[Any],
        retrieval_confidence: float = 0.8,
        use_cache: bool = True
    ) -> Any:
        context_hash = ",".join(sorted([c.chunk_id for c in candidates]))
        
        # 1. Attempt cache lookup
        if use_cache:
            cached = self.cache.get_answer(query, context_hash)
            if cached:
                from engine.answer_generation.answer_models import AnswerResult, GenerationMetrics
                from engine.answer_generation.verifier import VerificationResult
                
                # Reconstruct AnswerResult from cache
                metrics = GenerationMetrics(**cached["metrics"])
                verification = VerificationResult(
                    is_valid=cached["verification"]["is_valid"],
                    unsupported_claims=cached["verification"]["unsupported_claims"],
                    contradictions=cached["verification"]["contradictions"],
                    supported_claims=cached["verification"]["supported_claims"]
                )
                return AnswerResult(
                    text=cached["text"],
                    citations=cached["citations"],
                    verification=verification,
                    confidence=cached["confidence"],
                    metrics=metrics,
                    metadata=cached.get("metadata", {})
                )

        # 2. Call answer generation orchestrator
        res = self.orchestrator.generate_answer(
            query=query,
            qu=query_understanding,
            candidates=candidates,
            retrieval_confidence=retrieval_confidence
        )

        # 3. Cache answer
        if use_cache:
            serialized = {
                "text": res.text,
                "citations": res.citations,
                "confidence": res.confidence,
                "verification": {
                    "is_valid": res.verification.is_valid,
                    "unsupported_claims": res.verification.unsupported_claims,
                    "contradictions": res.verification.contradictions,
                    "supported_claims": res.verification.supported_claims
                },
                "metrics": {
                    "prompt_tokens": res.metrics.prompt_tokens,
                    "completion_tokens": res.metrics.completion_tokens,
                    "generation_time": res.metrics.generation_time,
                    "verification_time": res.metrics.verification_time,
                    "llm_cost": res.metrics.llm_cost,
                    "citation_count": res.metrics.citation_count,
                    "hallucination_rate": res.metrics.hallucination_rate,
                    "retry_count": res.metrics.retry_count,
                    "provider": res.metrics.provider,
                    "model": res.metrics.model
                },
                "metadata": res.metadata
            }
            self.cache.cache_answer(query, context_hash, serialized)

        return res
