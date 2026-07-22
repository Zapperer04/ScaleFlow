import os
from typing import List, Dict, Any
from engine.document_retrieval.candidate import Candidate
from engine.document_retrieval.query_understanding import QueryUnderstanding
from engine.answer_generation.context_formatter import ContextFormatter

class PromptBuilder:
    def __init__(self, prompts_dir: str = None):
        if prompts_dir is None:
            prompts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts")
        self.prompts_dir = prompts_dir
        self.context_formatter = ContextFormatter()

    def build_prompt(self, query: str, qu: QueryUnderstanding, candidates: List[Candidate]) -> str:
        # 1. Select template based on Query intent
        template_name = "default.txt"
        
        if qu:
            if qu.table_probability > 0.6:
                template_name = "table.txt"
            elif qu.graph_probability > 0.6:
                template_name = "reasoning.txt"
            elif qu.intent_distribution.get("comparison", 0.0) > 0.6:
                template_name = "comparison.txt"

        template_path = os.path.join(self.prompts_dir, template_name)
        if not os.path.exists(template_path):
            template_path = os.path.join(self.prompts_dir, "default.txt")

        with open(template_path, "r", encoding="utf-8") as f:
            template = f.read()

        # 2. Format Context
        formatted_context = self.context_formatter.format_candidates(candidates)

        # 3. Output prompt E2E
        return template.format(
            formatted_context=formatted_context,
            query=query
        )
