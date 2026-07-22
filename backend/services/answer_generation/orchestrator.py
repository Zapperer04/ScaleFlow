import time
from typing import List, Dict, Any, Optional

from services.document_retrieval.candidate import Candidate
from services.document_retrieval.query_understanding import QueryUnderstanding

from services.answer_generation.answer_models import AnswerResult, GenerationMetrics
from services.answer_generation.prompt_builder import PromptBuilder
from services.answer_generation.context_formatter import ContextFormatter
from services.answer_generation.citation_manager import CitationManager
from services.answer_generation.answer_generator import AnswerGenerator
from services.answer_generation.verifier import AnswerVerifier
from services.answer_generation.confidence import ConfidenceEngine
from services.answer_generation.answer_postprocessor import AnswerPostprocessor
from services.answer_generation.generation_metrics import GenerationMetricsCollector
from services.answer_generation.answer_planner import AnswerPlanner
from services.answer_generation.context_validator import ContextValidator

class AnswerOrchestrator:
    def __init__(self):
        self.prompt_builder = PromptBuilder()
        self.context_formatter = ContextFormatter()
        self.citation_manager = CitationManager()
        self.generator = AnswerGenerator()
        self.verifier = AnswerVerifier()
        self.confidence_engine = ConfidenceEngine()
        self.postprocessor = AnswerPostprocessor()
        self.metrics_collector = GenerationMetricsCollector()
        self.planner = AnswerPlanner()
        self.context_validator = ContextValidator()

    def generate_answer(
        self,
        query: str,
        qu: QueryUnderstanding,
        candidates: List[Candidate],
        retrieval_confidence: float = 0.8,
        max_retries: int = 1
    ) -> AnswerResult:
        start_time = time.time()
        
        # 1. Validate Context Candidates
        validated_candidates = self.context_validator.validate_context(candidates)

        # 2. Answer Planning
        plan = self.planner.create_plan(query, qu, validated_candidates)

        # 3. Build prompt incorporating plan
        prompt = self.prompt_builder.build_prompt(query, qu, validated_candidates)
        prompt += f"\n\nFollow this Execution Plan step-by-step:\n" + "\n".join(plan.plan_steps)

        draft_answer = ""
        prompt_tokens = 0
        completion_tokens = 0
        provider = "unknown"
        model = "unknown"
        retry_count = 0
        verification_time = 0.0

        # E2E Retry loop for verifier
        for attempt in range(max_retries + 1):
            retry_count = attempt
            gen_start = time.time()
            gen_res = self.generator.generate_answer(prompt)
            gen_time = time.time() - gen_start

            draft_answer = gen_res.get("text", "")
            prompt_tokens += gen_res.get("prompt_tokens", 0)
            completion_tokens += gen_res.get("completion_tokens", 0)
            provider = gen_res.get("provider", "unknown")
            model = gen_res.get("model", "unknown")

            # 2. Verification
            v_start = time.time()
            verification = self.verifier.verify(draft_answer, candidates)
            verification_time += time.time() - v_start

            # If valid, break and return
            if verification.is_valid:
                break
            elif attempt < max_retries:
                # Append reflection warning as LLM feedback for next retry
                feedback = (
                    f"\n\n[Verification Attempt {attempt+1} Failed]\n"
                    f"Your draft answer has verification errors:\n"
                    f"Unsupported Claims: {verification.unsupported_claims}\n"
                    f"Contradictions: {verification.contradictions}\n"
                    f"Please rewrite the answer to resolve all listed issues cleanly."
                )
                prompt += feedback

        # 3. Postprocess answer text
        final_text = self.postprocessor.postprocess(draft_answer)

        # 4. Citation parsing
        citations = self.citation_manager.parse_citations(final_text, candidates)

        # 5. Compute overall confidence
        confidence = self.confidence_engine.calculate_confidence(
            retrieval_confidence=retrieval_confidence,
            verification=verification,
            candidates=candidates,
            answer_text=final_text
        )

        total_time = time.time() - start_time
        cost = self.metrics_collector.calculate_cost(prompt_tokens, completion_tokens, provider)

        # 6. Build E2E metrics
        metrics = GenerationMetrics(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            generation_time=total_time - verification_time,
            verification_time=verification_time,
            llm_cost=cost,
            citation_count=len(citations),
            hallucination_rate=len(verification.unsupported_claims) / 10.0,
            retry_count=retry_count,
            provider=provider,
            model=model
        )

        return AnswerResult(
            text=final_text,
            citations=citations,
            verification=verification,
            confidence=confidence,
            metrics=metrics,
            metadata={
                "query": query,
                "raw_draft_answer": draft_answer
            }
        )
