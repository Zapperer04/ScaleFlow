import os
import json
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.dto.parsing import ParserResponseDTO
from backend.dto.chunking import ChunkDTO
from backend.dto.embedding import EmbeddingDTO
from backend.dto.retrieval import RetrievalRequestDTO, RetrievalResponseDTO
from backend.dto.pipeline import PipelineStateDTO
from backend.dto.graph import MetadataDTO, NodeDTO, EdgeDTO, GraphDTO

SCHEMAS_DIR = os.path.join("backend", "contracts", "schemas", "v1")
os.makedirs(SCHEMAS_DIR, exist_ok=True)

models = {
    "ParserResponse.json": ParserResponseDTO,
    "Chunk.json": ChunkDTO,
    "Graph.json": GraphDTO,
    "Node.json": NodeDTO,
    "Edge.json": EdgeDTO,
    "Metadata.json": MetadataDTO,
    "Embedding.json": EmbeddingDTO,
    "RetrievalRequest.json": RetrievalRequestDTO,
    "RetrievalResponse.json": RetrievalResponseDTO,
    "PipelineState.json": PipelineStateDTO,
}

for name, model in models.items():
    schema = model.model_json_schema()
    filepath = os.path.join(SCHEMAS_DIR, name)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)
    print(f"Generated {filepath}")
