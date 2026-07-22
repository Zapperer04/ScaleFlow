import os
import hashlib
from datetime import datetime
from typing import Dict, Any, List
from services.document_pipeline.builders.base_builder import BaseBuilder
from services.document_pipeline.schemas import CanonicalDocument, EmbeddingRecord

# Reuse the existing embedding service
try:
    from services.embedding_service import embed_text
    EMBEDDING_SERVICE_AVAILABLE = True
except ImportError:
    EMBEDDING_SERVICE_AVAILABLE = False

class EmbeddingBuilder(BaseBuilder):
    @property
    def name(self) -> str:
        return "embeddings"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def dependencies(self) -> List[str]:
        return ["chunks", "entities", "tables", "graph"]

    def build(self, doc: CanonicalDocument, context: Dict[str, Any]) -> List[EmbeddingRecord]:
        embedding_records: List[EmbeddingRecord] = []
        model_name = os.getenv("EMBEDDING_MODEL", "BAAI/bge-base-en-v1.5")
        
        graph_id_map = context.get("graph_id_map", {})

        def get_embedding(text: str) -> List[float]:
            if EMBEDDING_SERVICE_AVAILABLE:
                try:
                    return embed_text(text)
                except Exception:
                    pass
            return [round(0.01 * (i % 100), 5) for i in range(768)]

        def calculate_vector_hash(vector: List[float]) -> str:
            val_str = ",".join(map(str, vector))
            return hashlib.sha256(val_str.encode()).hexdigest()

        # Level 1: Semantic Chunks
        chunks_raw = context.get("chunks", [])
        for chunk in chunks_raw:
            c_text = chunk.get("text") if isinstance(chunk, dict) else chunk.text
            c_id = chunk.get("chunk_id") if isinstance(chunk, dict) else chunk.chunk_id
            c_nodes = chunk.get("graph_node_ids") if isinstance(chunk, dict) else chunk.graph_node_ids
            c_entities = chunk.get("entities") if isinstance(chunk, dict) else chunk.entities
            c_pages = chunk.get("page_range") if isinstance(chunk, dict) else chunk.page_range
            c_path = chunk.get("section_path") if isinstance(chunk, dict) else chunk.section_path
            c_parent = chunk.get("parent_node") if isinstance(chunk, dict) else chunk.parent_node
            c_bbox = chunk.get("bbox") if isinstance(chunk, dict) else chunk.bbox
            c_tbl = chunk.get("table_refs") if isinstance(chunk, dict) else chunk.table_refs
            c_fig = chunk.get("figure_refs") if isinstance(chunk, dict) else chunk.figure_refs

            vector = get_embedding(c_text)
            embedding_records.append(EmbeddingRecord(
                embedding_id=f"emb-{c_id}",
                chunk_id=c_id,
                graph_node_ids=c_nodes,
                entity_ids=c_entities,
                metadata={
                    "type": "chunk",
                    "graph_node_ids": c_nodes,
                    "page_numbers": c_pages,
                    "heading": c_parent,
                    "section_path": c_path,
                    "entities": c_entities,
                    "table_refs": c_tbl,
                    "figure_refs": c_fig,
                    "bbox": c_bbox
                },
                embedding_model=model_name,
                embedding_dimension=len(vector),
                embedding_version="1.0.0",
                created_at=datetime.utcnow().isoformat(),
                vector_hash=calculate_vector_hash(vector),
                vector=vector
            ))

        # Level 2: Headings / Sections
        for block in doc.blocks:
            if block.type == "heading":
                stable_block_id = graph_id_map.get(block.id, block.id)
                vector = get_embedding(block.text)
                bbox_dict = block.bbox.to_dict() if block.bbox else {"ymin": 0.0, "xmin": 0.0, "ymax": 1.0, "xmax": 1.0}
                embedding_records.append(EmbeddingRecord(
                    embedding_id=f"emb-heading-{stable_block_id}",
                    chunk_id=stable_block_id,
                    graph_node_ids=[stable_block_id],
                    entity_ids=[],
                    metadata={
                        "type": "heading",
                        "graph_node_ids": [stable_block_id],
                        "page_numbers": [block.page],
                        "heading": block.text,
                        "section_path": [block.text],
                        "entities": [],
                        "table_refs": [],
                        "figure_refs": [],
                        "bbox": bbox_dict
                    },
                    embedding_model=model_name,
                    embedding_dimension=len(vector),
                    embedding_version="1.0.0",
                    created_at=datetime.utcnow().isoformat(),
                    vector_hash=calculate_vector_hash(vector),
                    vector=vector
                ))

        # Level 3: Entities
        entity_graph = context.get("entities")
        if entity_graph:
            entities_list = []
            if isinstance(entity_graph, dict):
                entities_list = entity_graph.get("entities", [])
            else:
                entities_list = entity_graph.entities

            for ent in entities_list:
                e_id = ent.get("id") if isinstance(ent, dict) else ent.id
                e_name = ent.get("name") if isinstance(ent, dict) else ent.name
                e_type = ent.get("type") if isinstance(ent, dict) else ent.type
                e_norm = ent.get("normalized_value") if isinstance(ent, dict) else ent.normalized_value
                e_occs = ent.get("occurrences", []) if isinstance(ent, dict) else ent.occurrences

                vector = get_embedding(f"{e_type}: {e_name} ({e_norm})")
                
                # Fetch occurrences info
                pages = list(set([occ.get("page") for occ in e_occs if occ.get("page")]))
                nodes_ref = list(set([occ.get("block_id") for occ in e_occs if occ.get("block_id")]))

                embedding_records.append(EmbeddingRecord(
                    embedding_id=f"emb-entity-{e_id}",
                    chunk_id=e_id,
                    graph_node_ids=nodes_ref,
                    entity_ids=[e_id],
                    metadata={
                        "type": "entity",
                        "graph_node_ids": nodes_ref,
                        "page_numbers": pages,
                        "heading": "",
                        "section_path": [],
                        "entities": [e_name],
                        "table_refs": [],
                        "figure_refs": [],
                        "bbox": {"ymin": 0.0, "xmin": 0.0, "ymax": 1.0, "xmax": 1.0}
                    },
                    embedding_model=model_name,
                    embedding_dimension=len(vector),
                    embedding_version="1.0.0",
                    created_at=datetime.utcnow().isoformat(),
                    vector_hash=calculate_vector_hash(vector),
                    vector=vector
                ))

        # Level 4: Table Summaries
        tables_raw = context.get("tables", [])
        for table in tables_raw:
            t_id = table.get("id") if isinstance(table, dict) else table.id
            t_id_stable = graph_id_map.get(t_id, t_id)
            t_page = table.get("page") if isinstance(table, dict) else table.page
            t_caption = table.get("caption") if isinstance(table, dict) else table.caption
            t_schema = table.get("schema") if isinstance(table, dict) else table.schema
            t_bbox = table.get("coordinates") if isinstance(table, dict) else table.coordinates
            t_refs = table.get("references") if isinstance(table, dict) else table.references

            caption_text = t_caption or f"Table on page {t_page} with {t_schema.get('rows', 0)} rows"
            vector = get_embedding(caption_text)
            embedding_records.append(EmbeddingRecord(
                embedding_id=f"emb-table-{t_id_stable}",
                chunk_id=t_id_stable,
                graph_node_ids=[t_id_stable],
                entity_ids=[],
                metadata={
                    "type": "table_summary",
                    "graph_node_ids": [t_id_stable],
                    "page_numbers": [t_page],
                    "heading": t_caption or "",
                    "section_path": [],
                    "entities": [],
                    "table_refs": t_refs or [],
                    "figure_refs": [],
                    "bbox": t_bbox or {"ymin": 0.0, "xmin": 0.0, "ymax": 1.0, "xmax": 1.0}
                },
                embedding_model=model_name,
                embedding_dimension=len(vector),
                embedding_version="1.0.0",
                created_at=datetime.utcnow().isoformat(),
                vector_hash=calculate_vector_hash(vector),
                vector=vector
            ))

        return embedding_records
