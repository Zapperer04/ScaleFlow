import time
from typing import Dict, Any
from engine.answer_generation.answer_models import GenerationMetrics

class GenerationMetricsCollector:
    def calculate_cost(self, prompt_tokens: int, completion_tokens: int, provider: str) -> float:
        # Mock pricing: $1.00 per 1M prompt tokens, $2.00 per 1M completion tokens
        cost_prompt = (prompt_tokens / 1_000_000) * 1.0
        cost_completion = (completion_tokens / 1_000_000) * 2.0
        return cost_prompt + cost_completion
