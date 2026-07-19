from typing import List, Dict, Any, Optional
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

class DocumentFactory:
    @staticmethod
    def create(
        document_id: int,
        filename: str,
        pages_data: List[Dict[str, Any]],
        chunks_data: List[Dict[str, Any]] = None,
        graph_data: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None,
        artifacts_data: List[Dict[str, Any]] = None
    ) -> Document:
        pages = [Page.from_dict(p) for p in pages_data]
        chunks = [Chunk.from_dict(c) for c in (chunks_data or [])]
        graph = Graph.from_dict(graph_data) if graph_data else None
        artifacts = [Artifact.from_dict(a) for a in (artifacts_data or [])]
        return Document(
            document_id=DocumentId(document_id),
            filename=filename,
            pages=pages,
            chunks=chunks,
            graph=graph,
            metadata=metadata or {},
            artifacts=artifacts,
        )

class ChunkFactory:
    @staticmethod
    def create(
        chunk_id: str,
        chunk_index: int,
        chunk_text: str,
        page_number: int,
        file_id: int,
        pipeline_id: int,
        metadata: Dict[str, Any] = None,
        graph_relations: Any = None
    ) -> Chunk:
        return Chunk(
            chunk_id=ChunkId(chunk_id),
            chunk_index=chunk_index,
            chunk_text=chunk_text,
            page_number=PageNumber(page_number),
            file_id=file_id,
            pipeline_id=pipeline_id,
            metadata=metadata or {},
            graph_relations=graph_relations,
        )

class GraphFactory:
    @staticmethod
    def create(nodes_data: List[Dict[str, Any]], edges_data: List[Dict[str, Any]]) -> Graph:
        nodes = [
            Node(node_id=NodeId(n["node_id"]), label=n["label"], properties=n.get("properties", {}))
            for n in nodes_data
        ]
        edges = [
            Edge(
                source=NodeId(e["source"]),
                target=NodeId(e["target"]),
                relation=e["relation"],
                properties=e.get("properties", {}),
            )
            for e in edges_data
        ]
        return Graph(nodes=nodes, edges=edges)

class PipelineFactory:
    @staticmethod
    def create(
        pipeline_id: int,
        name: str,
        state: str,
        tasks: List[Dict[str, Any]] = None,
        artifacts_data: List[Dict[str, Any]] = None,
        events: List[Dict[str, Any]] = None
    ) -> Pipeline:
        artifacts = [Artifact.from_dict(a) for a in (artifacts_data or [])]
        return Pipeline(
            pipeline_id=PipelineId(pipeline_id),
            name=name,
            state=PipelineState(state),
            tasks=tasks or [],
            artifacts=artifacts,
            events=events or [],
        )
