from dataclasses import dataclass
from typing import Dict, Any, Optional
from datetime import datetime

@dataclass(frozen=True)
class DomainEvent:
    event_id: str
    timestamp: str

@dataclass(frozen=True)
class DocumentUploaded(DomainEvent):
    document_id: int
    filename: str
    size_bytes: int

@dataclass(frozen=True)
class DocumentParsed(DomainEvent):
    document_id: int
    pages_count: int
    parser_used: str

@dataclass(frozen=True)
class ChunkCreated(DomainEvent):
    chunk_id: str
    document_id: int
    chunk_index: int

@dataclass(frozen=True)
class EmbeddingCreated(DomainEvent):
    chunk_id: str
    vector_dimension: int

@dataclass(frozen=True)
class IndexCreated(DomainEvent):
    pipeline_id: int
    index_type: str

@dataclass(frozen=True)
class RetrievalCompleted(DomainEvent):
    query: str
    results_count: int

@dataclass(frozen=True)
class PipelineCompleted(DomainEvent):
    pipeline_id: int
    duration_seconds: float

@dataclass(frozen=True)
class PipelineFailed(DomainEvent):
    pipeline_id: int
    error_message: str
