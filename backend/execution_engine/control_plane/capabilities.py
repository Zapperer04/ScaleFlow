import os
import yaml
from typing import Dict, Any
from execution_engine.control_plane.interfaces import CapabilityRegistry

class YamlCapabilityRegistry(CapabilityRegistry):
    """
    CapabilityRegistry that loads provider capabilities dynamically
    from YAML manifest files, decoupling provider configurations from scheduler logic.
    """
    def __init__(self, manifests_dir: str = "execution_engine/core/manifests"):
        self.manifests_dir = manifests_dir
        self.capabilities: Dict[str, Dict[str, Any]] = {}
        self.load_manifests()

    def load_manifests(self):
        if not os.path.exists(self.manifests_dir):
            os.makedirs(self.manifests_dir, exist_ok=True)
            # Create a default gemini manifest as a placeholder
            default_gemini = {
                "provider": "gemini",
                "supports": {
                    "streaming": True,
                    "multimodal": True,
                    "json_schema": True
                },
                "limits": {
                    "max_context": 1000000,
                    "max_image_resolution": 4096
                },
                "cost": {
                    "estimated_latency": "medium",
                    "quota_weight": "high"
                },
                "health": 100.0,
                "quota_available": 100.0
            }
            with open(os.path.join(self.manifests_dir, "gemini.yaml"), "w") as f:
                yaml.dump(default_gemini, f)

        for filename in os.listdir(self.manifests_dir):
            if filename.endswith(".yaml") or filename.endswith(".yml"):
                filepath = os.path.join(self.manifests_dir, filename)
                with open(filepath, "r") as f:
                    data = yaml.safe_load(f)
                    if data and "provider" in data:
                        # Flatten structure slightly for broker consumption
                        provider_id = data["provider"]
                        self.capabilities[provider_id] = {
                            "supports_images": data.get("supports", {}).get("multimodal", False),
                            "supports_streaming": data.get("supports", {}).get("streaming", False),
                            "max_context": data.get("limits", {}).get("max_context", 4096),
                            "health": data.get("health", 100.0),
                            "quota_available": data.get("quota_available", 100.0)
                        }

    def register_provider(self, provider_id: str, capabilities: dict) -> None:
        self.capabilities[provider_id] = capabilities

    def get_capabilities(self, provider_id: str) -> dict:
        return self.capabilities.get(provider_id, {})
