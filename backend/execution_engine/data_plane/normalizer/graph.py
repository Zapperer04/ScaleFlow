from typing import Dict, Any

class GraphNormalizer:
    """
    Normalizes provider-specific ASTs into the canonical ScaleFlow Graph format.
    """
    def normalize(self, raw_ast: Dict[str, Any], provider_id: str) -> Dict[str, Any]:
        """
        Maps schema quirks (e.g., heading_level -> level).
        """
        canonical = {}
        # MVP: just pass through or apply basic mappings
        if provider_id == "gemini":
            canonical["nodes"] = raw_ast.get("nodes", [])
        elif provider_id == "openrouter":
            canonical["nodes"] = raw_ast.get("elements", [])
        else:
            canonical["nodes"] = raw_ast.get("nodes", [])
            
        return canonical
