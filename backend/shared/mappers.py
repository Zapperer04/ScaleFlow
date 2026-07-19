import json
from typing import Dict, Any, List

from backend.domain.value_objects.document_id import DocumentId
from backend.domain.value_objects.pipeline_id import PipelineId
from backend.domain.value_objects.chunk_id import ChunkId
from backend.domain.value_objects.page_number import PageNumber
from backend.domain.value_objects.node_id import NodeId
from backend.domain.value_objects.bounding_box import BoundingBox
from backend.domain.value_objects.coordinates import Coordinates
from backend.domain.value_objects.embedding_vector import EmbeddingVector

from backend.domain.entities.page import Page
from backend.domain.entities.chunk import Chunk
from backend.domain.entities.node import Node
from backend.domain.entities.edge import Edge
from backend.domain.entities.graph import Graph
from backend.domain.entities.artifact import Artifact
from backend.domain.entities.embedding import Embedding
from backend.domain.entities.retrieval import Retrieval

from backend.domain.aggregates.document import Document
from backend.domain.aggregates.pipeline import Pipeline
from backend.domain.states import PipelineState

from backend.dto.parsing import ParserResponseDTO
from backend.dto.chunking import ChunkDTO
from backend.dto.embedding import EmbeddingDTO
from backend.dto.retrieval import RetrievalRequestDTO, RetrievalResponseDTO
from backend.dto.worker import WorkerTaskDTO
from backend.dto.pipeline import PipelineStateDTO
from backend.dto.storage import StorageArtifactDTO
from backend.dto.graph import MetadataDTO, NodeDTO, EdgeDTO, GraphDTO

# Dict <-> Domain
def dict_to_page(data: Dict[str, Any]) -> Page:
    return Page.from_dict(data)

def page_to_dict(page: Page) -> Dict[str, Any]:
    return page.to_dict()

def dict_to_chunk(data: Dict[str, Any]) -> Chunk:
    return Chunk.from_dict(data)

def chunk_to_dict(chunk: Chunk) -> Dict[str, Any]:
    return chunk.to_dict()

def dict_to_graph(data: Dict[str, Any]) -> Graph:
    return Graph.from_dict(data)

def graph_to_dict(graph: Graph) -> Dict[str, Any]:
    return graph.to_dict()

def dict_to_artifact(data: Dict[str, Any]) -> Artifact:
    return Artifact.from_dict(data)

def artifact_to_dict(artifact: Artifact) -> Dict[str, Any]:
    return artifact.to_dict()

def dict_to_embedding(data: Dict[str, Any]) -> Embedding:
    return Embedding.from_dict(data)

def embedding_to_dict(embedding: Embedding) -> Dict[str, Any]:
    return embedding.to_dict()

def dict_to_retrieval(data: Dict[str, Any]) -> Retrieval:
    return Retrieval.from_dict(data)

def retrieval_to_dict(retrieval: Retrieval) -> Dict[str, Any]:
    return retrieval.to_dict()

def dict_to_pipeline(data: Dict[str, Any]) -> Pipeline:
    return Pipeline.from_dict(data)

def pipeline_to_dict(pipeline: Pipeline) -> Dict[str, Any]:
    return pipeline.to_dict()

def dict_to_document(data: Dict[str, Any]) -> Document:
    return Document.from_dict(data)

def document_to_dict(document: Document) -> Dict[str, Any]:
    return document.to_dict()

# JSON <-> Domain
def json_to_document(js: str) -> Document:
    return dict_to_document(json.loads(js))

def document_to_json(doc: Document) -> str:
    return json.dumps(document_to_dict(doc))

# DTO <-> Domain
def dto_to_chunk(dto: ChunkDTO) -> Chunk:
    return Chunk(
        chunk_id=ChunkId(dto.chunk_id),
        chunk_index=dto.chunk_index,
        chunk_text=dto.chunk_text,
        page_number=PageNumber(dto.page_number),
        file_id=dto.file_id,
        pipeline_id=dto.pipeline_id,
        metadata=dto.metadata,
        graph_relations=dto.graph_relations,
    )

def chunk_to_dto(chunk: Chunk) -> ChunkDTO:
    return ChunkDTO(
        chunk_id=chunk.chunk_id.value,
        chunk_index=chunk.chunk_index,
        chunk_text=chunk.chunk_text,
        page_number=chunk.page_number.value,
        file_id=chunk.file_id,
        pipeline_id=chunk.pipeline_id,
        metadata=chunk.metadata,
        graph_relations=chunk.graph_relations,
    )

def dto_to_embedding(dto: EmbeddingDTO) -> Embedding:
    return Embedding(
        chunk_id=ChunkId(dto.chunk_id),
        embedding_vector=EmbeddingVector(dto.embedding_vector),
        metadata=dto.metadata,
    )

def embedding_to_dto(emb: Embedding) -> EmbeddingDTO:
    return EmbeddingDTO(
        chunk_id=emb.chunk_id.value,
        embedding_vector=emb.embedding_vector.values,
        metadata=emb.metadata,
    )

def dto_to_artifact(dto: StorageArtifactDTO) -> Artifact:
    return Artifact(
        artifact_id=DocumentId(dto.artifact_id) if dto.artifact_id is not None else None,
        pipeline_id=PipelineId(dto.pipeline_id),
        task_id=dto.task_id,
        artifact_type=dto.artifact_type,
        storage_uri=dto.storage_uri,
        metadata_json=dto.metadata_json,
        checksum=dto.checksum,
    )

def artifact_to_dto(art: Artifact) -> StorageArtifactDTO:
    return StorageArtifactDTO(
        artifact_id=art.artifact_id.value if art.artifact_id else None,
        pipeline_id=art.pipeline_id.value,
        task_id=art.task_id,
        artifact_type=art.artifact_type,
        storage_uri=art.storage_uri,
        metadata_json=art.metadata_json,
        checksum=art.checksum,
    )

def dto_to_pipeline(dto: PipelineStateDTO) -> Pipeline:
    return Pipeline(
        pipeline_id=PipelineId(dto.pipeline_id),
        name=dto.name,
        state=PipelineState(dto.state),
        metadata=dto.metadata,
    )

def pipeline_to_dto(pipeline: Pipeline) -> PipelineStateDTO:
    return PipelineStateDTO(
        pipeline_id=pipeline.pipeline_id.value,
        name=pipeline.name,
        state=pipeline.state.value,
    )
