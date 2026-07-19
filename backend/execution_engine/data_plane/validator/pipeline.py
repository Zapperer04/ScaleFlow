from typing import Dict, Any
import json
from execution_engine.data_plane.normalizer.graph import GraphNormalizer
from execution_engine.core.context import ExecutionContext
from execution_engine.core.events import EventType

class ValidationPipeline:
    def __init__(self, normalizer: GraphNormalizer):
        self.normalizer = normalizer
        
    def validate(self, raw_output: str, ctx: ExecutionContext) -> Dict[str, Any]:
        try:
            raw_ast = json.loads(raw_output)
        except json.JSONDecodeError as e:
            ctx.logger.error(f"Syntax validation failed: {e}")
            raise Exception("Malformed JSON")
        canonical_graph = self.normalizer.normalize(raw_ast, ctx.provider_id)
        ctx.emit(EventType.JSON_VALIDATED)
        return canonical_graph
