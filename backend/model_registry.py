import os

class ModelRegistry:
    def __init__(self):
        self.registry = {
            "embedding": {
                "id": "BAAI/bge-base-en-v1.5",
                "version": "1.5.0",
                "parameter_size": "109M",
                "provider": "HuggingFace",
                "description": "Bi-encoder model for high quality sentence embeddings"
            },
            "reranker": {
                "id": "BAAI/bge-reranker-large",
                "version": "1.0.0",
                "parameter_size": "335M",
                "provider": "HuggingFace",
                "description": "Cross-encoder model for high precision reranking"
            },
            "ocr": {
                "id": "tesseract-ocr",
                "version": "5.3.0",
                "parameter_size": "N/A",
                "provider": "System",
                "description": "Tesseract open-source OCR engine"
            },
            "vlm": {
                "id": "google/gemini-2.0-flash",
                "version": "2.0.0",
                "parameter_size": "N/A",
                "provider": "Google",
                "description": "Multimodal vision-language model for parsing and understanding complex documents"
            },
            "llm": {
                "id": "google/gemini-2.5-flash",
                "version": "2.5.0",
                "parameter_size": "N/A",
                "provider": "Google",
                "description": "Primary large language model for generation and context synthesis"
            }
        }

    def get_model_info(self, model_type: str) -> dict:
        """Get info about a model type (e.g. embedding, reranker, ocr, vlm, llm)"""
        return self.registry.get(model_type, {})

    def get_model_version(self, model_type: str) -> str:
        """Get model version"""
        return self.registry.get(model_type, {}).get("version", "unknown")

    def get_all_models(self) -> dict:
        """Returns the full model registry"""
        return self.registry

model_registry = ModelRegistry()
