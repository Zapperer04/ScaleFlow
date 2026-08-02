import os
from typing import List, Dict, Any, Tuple
from services.pdf_parser import parse_pdf
from document_graph import DocumentGraph
from spatial_chunker import SpatialChunker
from services.embedding_service import embed_text
from services.vector_store import upsert_document_chunks
from services.bm25_service import rebuild_bm25_index
from context.artifact_store import save_artifact_to_disk

class IngestionPipeline:
    def __init__(self, max_tokens: int = 512):
        self.chunker = SpatialChunker(max_tokens=max_tokens)

    def run_ingestion(self, filepath: str, pipeline_id: int, file_id: int, task_id: int) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        # 1. Parse document using existing VLM / OCR PDF parser
        print(f"[INGESTION] Parsing PDF: {filepath}", flush=True)
        parse_result = parse_pdf(filepath, task_id=str(task_id))
        
        raw_graph = parse_result.document_graph if hasattr(parse_result, "document_graph") else {}
        if not raw_graph and isinstance(parse_result, dict):
            raw_graph = parse_result.get("document_graph", {})

        # 2. Canonicalize Layout Graph JSON (Deterministic & Versioned)
        doc_id = str(pipeline_id)
        doc_graph = DocumentGraph(document_id=doc_id, version=1, schema="document-graph-v1")
        
        # Populate nodes/edges from parser output
        pages = raw_graph.get("pages", [])
        for page in pages:
            doc_graph.add_page(
                page_number=page.get("page_number", 1),
                width=page.get("width", 612.0),
                height=page.get("height", 792.0),
                metadata=page.get("metadata", {})
            )
            
            # Map raw nodes to document graph node schema
            for node in page.get("nodes", []):
                doc_graph.add_node(
                    node_id=node.get("chunk_id") or node.get("id"),
                    node_type=node.get("type") or node.get("structural_type", "paragraph"),
                    page=page.get("page_number", 1),
                    text=node.get("text", ""),
                    bbox=node.get("bbox"),
                    parent=node.get("parent"),
                    children=node.get("children", []),
                    reading_order=node.get("reading_order", 0),
                    metadata=node.get("metadata", {})
                )

        for edge in raw_graph.get("edges", []):
            doc_graph.add_edge(
                source=edge.get("source") or edge.get("from_id"),
                target=edge.get("target") or edge.get("to_id"),
                edge_type=edge.get("type") or edge.get("relation", "contains"),
                metadata=edge.get("metadata", {})
            )

        graph_dict = doc_graph.to_dict()

        # 3. Build Spatial Chunks
        print(f"[INGESTION] Splitting document into spatial chunks", flush=True)
        chunks = self.chunker.chunk_document(graph_dict)

        # 4. Generate Embeddings & Index to Qdrant
        print(f"[INGESTION] Generating embeddings for {len(chunks)} chunks", flush=True)
        vectors = []
        # Ingestion requires embedding_id and bm25_doc_id in each chunk
        for chunk in chunks:
            # Generate embedding
            vec = embed_text(chunk["text"])
            vectors.append(vec)
            
            # Map semantic/BM25 indexing payload attributes
            chunk["chunk_text"] = chunk["text"]
            chunk["content_type"] = chunk["section_id"]
            chunk["pipeline_id"] = pipeline_id
            chunk["file_id"] = file_id

        # Upsert chunks to Qdrant
        print(f"[INGESTION] Upserting to Qdrant", flush=True)
        success, _, _, _ = upsert_document_chunks(
            pipeline_id=pipeline_id,
            file_id=file_id,
            task_id=task_id,
            chunks=chunks,
            vectors=vectors,
            collection_name="scaleflow_chunks"
        )
        if not success:
            print("[INGESTION] Warning: Qdrant upsert unsuccessful", flush=True)

        # 5. Build BM25 index
        print(f"[INGESTION] Rebuilding BM25 index", flush=True)
        rebuild_bm25_index(pipeline_id=pipeline_id, chunks=chunks)

        # 6. Save Artifacts to Disk
        print(f"[INGESTION] Saving layout graph and chunks artifacts", flush=True)
        save_artifact_to_disk(pipeline_id, task_id, "document_graph", graph_dict)
        save_artifact_to_disk(pipeline_id, task_id, "text_chunks", chunks)

        return graph_dict, chunks
