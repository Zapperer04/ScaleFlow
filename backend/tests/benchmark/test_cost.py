import pytest
import os
import sys

# Ensure backend directory is in path
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

def calculate_estimated_cost(prompt_tokens, completion_tokens, provider, model):
    # Standard pricing lookup
    prices = {
        "gemini": {"input": 0.075 / 1000000, "output": 0.3 / 1000000},
        "openrouter": {"input": 0.50 / 1000000, "output": 1.50 / 1000000}
    }
    rates = prices.get(provider.lower(), {"input": 0.0, "output": 0.0})
    return (prompt_tokens * rates["input"]) + (completion_tokens * rates["output"])

def test_cost_calculation():
    # Test for Gemini model prices
    cost = calculate_estimated_cost(1000000, 1000000, "gemini", "gemini-1.5-flash")
    assert cost == 0.075 + 0.3
    
    # Test for unknown provider
    cost_unknown = calculate_estimated_cost(100, 100, "unknown", "model")
    assert cost_unknown == 0.0
