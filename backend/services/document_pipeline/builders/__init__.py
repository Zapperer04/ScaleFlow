from services.document_pipeline.builders.base_builder import BaseBuilder
from services.document_pipeline.builders.metadata_builder import MetadataBuilder
from services.document_pipeline.builders.layout_builder import LayoutBuilder
from services.document_pipeline.builders.entity_builder import EntityBuilder
from services.document_pipeline.builders.graph_builder import GraphBuilder
from services.document_pipeline.builders.chunk_builder import ChunkBuilder
from services.document_pipeline.builders.table_builder import TableBuilder
from services.document_pipeline.builders.embedding_builder import EmbeddingBuilder

ALL_BUILDERS = [
    MetadataBuilder(),
    LayoutBuilder(),
    EntityBuilder(),
    GraphBuilder(),
    ChunkBuilder(),
    TableBuilder(),
    EmbeddingBuilder()
]
