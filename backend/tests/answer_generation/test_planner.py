import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine.document_retrieval.query_understanding import QueryUnderstanding
from engine.answer_generation.answer_planner import AnswerPlanner

def test_planner_steps():
    planner = AnswerPlanner()
    qu = QueryUnderstanding(query="Compare the results", table_probability=0.1)
    # Simulate comparison intent distribution
    qu.intent_distribution["comparison"] = 0.8
    
    plan = planner.create_plan("Compare the results", qu, [])
    assert plan.format_instruction == "comparison"
    assert any("Contrast similarities" in step for step in plan.plan_steps)
