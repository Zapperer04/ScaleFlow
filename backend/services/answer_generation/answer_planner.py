from dataclasses import dataclass, field
from typing import List, Dict, Any
from services.document_retrieval.candidate import Candidate
from services.document_retrieval.query_understanding import QueryUnderstanding

@dataclass
class ExecutionPlan:
    query: str
    plan_steps: List[str] = field(default_factory=list)
    required_information: List[str] = field(default_factory=list)
    format_instruction: str = "general"

class AnswerPlanner:
    def create_plan(self, query: str, qu: QueryUnderstanding, candidates: List[Candidate]) -> ExecutionPlan:
        plan_steps = ["Analyze retrieved context and identify key facts."]
        required_info = []
        format_inst = "narrative"

        query_lower = query.lower()

        # 1. Infer plan steps based on Query intent
        if qu:
            if qu.table_probability > 0.6:
                plan_steps.append("Identify specific rows, headers, and cell values from unflattened Table evidence.")
                plan_steps.append("Compile tabular values into a structured Markdown Table.")
                required_info.append("tabular structures")
                format_inst = "table"

            if qu.graph_probability > 0.6:
                plan_steps.append("Trace graph node connections (headings, section parents, references).")
                plan_steps.append("Explain relational and parent-child hierarchy in structural sequence.")
                required_info.append("hierarchical structure")
                format_inst = "graph_traversal"

            if qu.intent_distribution.get("comparison", 0.0) > 0.6:
                plan_steps.append("Contrast similarities and differences across the retrieved candidates.")
                plan_steps.append("Draft comparative bullet points.")
                required_info.append("comparative attributes")
                format_inst = "comparison"

        # 2. General fallback
        plan_steps.append("Answer the user query citing matching sources using bracket numbers.")

        return ExecutionPlan(
            query=query,
            plan_steps=plan_steps,
            required_information=required_info,
            format_instruction=format_inst
        )
