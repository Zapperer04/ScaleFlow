import hashlib
import time

class PromptRegistry:
    def __init__(self):
        self.prompts = {
            "context_fusion": {
                "prompt_id": "context_fusion_v1",
                "version": "1.0.0",
                "created_at": "2026-08-02T12:00:00Z",
                "description": "Fuses multiple retrieved chunks and graph contexts into a single coherent prompt background.",
                "template": (
                    "Context Information from multiple source documents is provided below:\n"
                    "---------------------\n"
                    "{formatted_context}\n"
                    "---------------------\n"
                    "Given the context, synthesize the facts into a precise answer. Cite sources using [Chunk X] or [Node Y]."
                )
            },
            "graph_rag_expansion": {
                "prompt_id": "graph_rag_expansion_v1",
                "version": "1.0.0",
                "created_at": "2026-08-02T12:00:00Z",
                "description": "Generates supplementary entities or relations to explore in the document graph given a user query.",
                "template": (
                    "Analyze the user query: {query}\n"
                    "Identify key entities, relationships, or conceptual nodes that would be found in a hierarchical document graph."
                )
            },
            "qa_generation": {
                "prompt_id": "qa_generation_v1",
                "version": "1.1.0",
                "created_at": "2026-08-02T14:30:00Z",
                "description": "Core QA response generator prompt for the LLM.",
                "template": (
                    "You are ScaleFlow's RAG Assistant. Answer the query: '{query}' based on the provided context.\n"
                    "Context:\n"
                    "{context}\n\n"
                    "Return a clear answer with precise citations mapping back to sources."
                )
            }
        }

        # Calculate hashes dynamically
        for p_id, info in self.prompts.items():
            info["hash"] = hashlib.sha256(info["template"].encode("utf-8")).hexdigest()[:16]

    def get_prompt(self, prompt_id: str) -> dict:
        """Returns the prompt template info dictionary"""
        return self.prompts.get(prompt_id, {})

    def format_prompt(self, prompt_id: str, **kwargs) -> tuple:
        """Formats the prompt with kwargs, returning (formatted_string, version_meta)"""
        info = self.prompts.get(prompt_id)
        if not info:
            raise ValueError(f"Prompt with ID {prompt_id} not found.")
        formatted = info["template"].format(**kwargs)
        meta = {
            "prompt_id": info["prompt_id"],
            "version": info["version"],
            "hash": info["hash"],
            "created_at": info["created_at"]
        }
        return formatted, meta

    def get_all_prompts(self) -> dict:
        return self.prompts

prompt_registry = PromptRegistry()
