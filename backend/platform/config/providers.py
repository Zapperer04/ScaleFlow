import os

# Registry of supported models and their backup options
MODEL_REGISTRY = {
    "google/gemma-4-26b-a4b-it:free": {
        "primary": "openrouter",
        "fallback": ["openai", "ollama"],
        "cost_per_1k_input": 0.0,
        "cost_per_1k_output": 0.0,
    },
    "google/gemini-2.5-flash": {
        "primary": "gemini",
        "fallback": ["openrouter"],
        "cost_per_1k_input": 0.000075,
        "cost_per_1k_output": 0.0003,
    },
    "gpt-4o-mini": {
        "primary": "openai",
        "fallback": ["openrouter"],
        "cost_per_1k_input": 0.00015,
        "cost_per_1k_output": 0.0006,
    },
    "claude-3-5-sonnet": {
        "primary": "anthropic",
        "fallback": ["openrouter"],
        "cost_per_1k_input": 0.003,
        "cost_per_1k_output": 0.015,
    }
}

# API configuration keys
PROVIDER_KEYS = {
    "openrouter": os.getenv("OPENROUTER_API_KEY", ""),
    "openai": os.getenv("OPENAI_API_KEY", ""),
    "gemini": os.getenv("GEMINI_API_KEY", ""),
    "anthropic": os.getenv("ANTHROPIC_API_KEY", ""),
}

# Default model configuration
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "google/gemma-4-26b-a4b-it:free")
