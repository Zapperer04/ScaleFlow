import os
import time
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime

from services.document_pipeline.schemas import CanonicalDocument
from services.document_pipeline.parser import VLMParser
from services.document_pipeline.normalizer import CanonicalNormalizer
from services.document_pipeline.storage import DocumentStore
from services.document_pipeline.registry import DocumentRegistry, BuilderRegistry

class ProductionParsingOrchestrator:
    def __init__(self, base_dir: str = None):
        self.store = DocumentStore(base_dir)
        self.registry = DocumentRegistry(
            os.path.join(self.store.base_dir, "registry.db") if base_dir else None
        )
        self.builder_registry = BuilderRegistry()
        self.parser = VLMParser()
        self.normalizer = CanonicalNormalizer()

    def process_document(self, filepath: str, force_reparse: bool = False, trace_fn = None) -> str:
        """
        Runs the full pipeline:
        PDF -> Parser -> Normalizer -> Canonical Document -> All Builders -> Storage & Registry
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"PDF file not found: {filepath}")

        # Compute document ID based on hash of the PDF file
        hasher = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                hasher.update(chunk)
        doc_hash = hasher.hexdigest()

        # Check if already parsed
        if self.store.exists(doc_hash, "document.json") and not force_reparse:
            if trace_fn:
                trace_fn(f"[Orchestrator] Document {doc_hash} already parsed. Re-running builders if needed.")
            return self.rebuild_representations(doc_hash, force=True, trace_fn=trace_fn)

        if trace_fn:
            trace_fn(f"[Orchestrator] Parsing new document: {filepath}")

        # 1. Parse PDF using VLM
        raw_output = self.parser.parse(filepath, trace_fn=trace_fn)

        # 2. Normalize raw output into Canonical Document
        doc = self.normalizer.normalize(raw_output)
        doc.document_id = doc_hash  # Override with file content hash

        # Save Canonical Document
        self.store.save_json(doc_hash, "document.json", doc)

        # 3. Run all builders
        self._execute_builders(doc, list(self.builder_registry.builders.keys()), trace_fn=trace_fn)

        return doc_hash

    def rebuild_representations(self, document_id: str, targets: List[str] = None, force: bool = False, trace_fn = None) -> str:
        """
        Incremental rebuild support. Loads the Canonical Document and rebuilds only the specified targets (and downstream dependencies).
        """
        # Load Canonical Document
        doc_dict = self.store.load_json(document_id, "document.json")
        if not doc_dict:
            raise ValueError(f"Canonical document not found for {document_id}. Cannot rebuild.")

        # Re-construct Canonical Document object
        from services.document_pipeline.schemas.definitions import CanonicalBlock, CanonicalTable, CanonicalEntity
        
        blocks = []
        for b in doc_dict.get("blocks", []):
            bbox = None
            if b.get("bbox"):
                from services.document_pipeline.schemas import BoundingBox
                bbox = BoundingBox(**b["bbox"])
            blocks.append(CanonicalBlock(
                id=b["id"],
                type=b["type"],
                text=b["text"],
                page=b["page"],
                bbox=bbox,
                confidence=b.get("confidence", 1.0),
                metadata=b.get("metadata", {})
            ))

        tables = []
        for t in doc_dict.get("tables", []):
            bbox = None
            if t.get("bbox"):
                from services.document_pipeline.schemas import BoundingBox
                bbox = BoundingBox(**t["bbox"])
            tables.append(CanonicalTable(
                id=t["id"],
                page=t["page"],
                rows=t["rows"],
                columns=t["columns"],
                headers=t.get("headers", []),
                cells=t.get("cells", []),
                merged_cells=t.get("merged_cells", []),
                bbox=bbox,
                caption=t.get("caption"),
                references=t.get("references", [])
            ))

        entities = []
        for e in doc_dict.get("entities", []):
            entities.append(CanonicalEntity(
                name=e["name"],
                type=e["type"],
                normalized_value=e["normalized_value"],
                occurrences=e.get("occurrences", [])
            ))

        doc = CanonicalDocument(
            document_id=doc_dict["document_id"],
            pages=doc_dict.get("pages", []),
            blocks=blocks,
            layout=doc_dict.get("layout", {}),
            tables=tables,
            figures=doc_dict.get("figures", []),
            metadata=doc_dict.get("metadata", {}),
            entities=entities,
            parser_metadata=doc_dict.get("parser_metadata", {})
        )

        if targets is None:
            # Rebuild everything
            targets = list(self.builder_registry.builders.keys())

        # Dependency Invalidation logic
        ordered_builders = self.builder_registry.get_ordered_builders(targets)
        ordered_names = [b.name for b in ordered_builders]

        if trace_fn:
            trace_fn(f"[Orchestrator] Incremental rebuild for {document_id}. Targets: {targets}. Ordered execution path: {ordered_names}")

        self._execute_builders(doc, ordered_names, trace_fn=trace_fn)
        return document_id

    def _execute_builders(self, doc: CanonicalDocument, builder_names: List[str], trace_fn = None):
        doc_hash = doc.document_id
        context = {}

        # Load existing builders output to context for those that are not being rebuilt
        for name, builder in self.builder_registry.builders.items():
            if name not in builder_names:
                # Load from store
                if name == "graph":
                    nodes = self.store.load_json(doc_hash, "graph/nodes.json")
                    edges = self.store.load_json(doc_hash, "graph/edges.json")
                    if nodes is not None and edges is not None:
                        context["graph"] = {"nodes": nodes, "edges": edges}
                elif name == "chunks":
                    chunks = self.store.load_json(doc_hash, "chunks/chunks.json")
                    if chunks is not None:
                        # Convert to SemanticChunk objects
                        from services.document_pipeline.schemas import SemanticChunk
                        context["chunks"] = [SemanticChunk(**c) for c in chunks]
                else:
                    context[name] = self.store.load_json(doc_hash, f"{name}/{name}.json")

        # Get topological execution list for the builders to run
        ordered_to_run = self.builder_registry.get_ordered_builders(builder_names)

        # Run each builder in dependency order
        for builder in ordered_to_run:
            if trace_fn:
                trace_fn(f"[Orchestrator] Executing Builder: {builder.name} (v{builder.version})")
            
            output = builder.build(doc, context)
            context[builder.name] = output

            # Save builder output to storage
            if builder.name == "graph":
                self.store.save_json(doc_hash, "graph/nodes.json", output["nodes"])
                self.store.save_json(doc_hash, "graph/edges.json", output["edges"])
            elif builder.name == "chunks":
                self.store.save_json(doc_hash, "chunks/chunks.json", output)
            elif builder.name == "entities":
                self.store.save_json(doc_hash, "entities/entities.json", output)
            elif builder.name == "tables":
                self.store.save_json(doc_hash, "tables/tables.json", output)
            elif builder.name == "layout":
                self.store.save_json(doc_hash, "layout/layout.json", output)
            elif builder.name == "metadata":
                self.store.save_json(doc_hash, "metadata/metadata.json", output)
            elif builder.name == "embeddings":
                self.store.save_json(doc_hash, "embeddings/vectors.json", output)

        # Build Manifest
        manifest = self._generate_manifest(doc_hash, context)
        self.store.save_json(doc_hash, "manifest.json", manifest)

        # Register document
        available = []
        for name in self.builder_registry.builders.keys():
            if name == "graph":
                if self.store.exists(doc_hash, "graph/nodes.json"):
                    available.append("graph")
            elif self.store.exists(doc_hash, f"{name}/{name}.json"):
                available.append(name)

        versions = {name: self.builder_registry.get_builder(name).version for name in self.builder_registry.builders.keys()}
        
        # Calculate file hashes
        hashes = {}
        for r_name in available:
            if r_name == "graph":
                hashes["graph_nodes"] = self._file_hash(doc_hash, "graph/nodes.json")
                hashes["graph_edges"] = self._file_hash(doc_hash, "graph/edges.json")
            else:
                hashes[r_name] = self._file_hash(doc_hash, f"{r_name}/{r_name}.json")

        dependencies = {name: self.builder_registry.get_builder(name).dependencies for name in self.builder_registry.builders.keys()}
        self.registry.register_document(
            document_id=doc_hash,
            versions=versions,
            hashes=hashes,
            dependencies=dependencies,
            available_representations=available,
            builder_outputs={
                "parser": doc.parser_metadata.get("parser_used", "vlm"),
                "total_pages": len(doc.pages)
            }
        )


    def _file_hash(self, doc_id: str, relative_path: str) -> str:
        doc_dir = self.store._get_doc_dir(doc_id)
        path = os.path.join(doc_dir, relative_path)
        if not os.path.exists(path):
            return ""
        hasher = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b''):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _generate_manifest(self, doc_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        versions = {name: self.builder_registry.get_builder(name).version for name in self.builder_registry.builders.keys()}
        
        # Calculate hashes
        hashes = {
            "document": self._file_hash(doc_id, "document.json")
        }
        for name in self.builder_registry.builders.keys():
            if name == "graph":
                hashes["graph_nodes"] = self._file_hash(doc_id, "graph/nodes.json")
                hashes["graph_edges"] = self._file_hash(doc_id, "graph/edges.json")
            else:
                hashes[name] = self._file_hash(doc_id, f"{name}/{name}.json")

        now = datetime.utcnow().isoformat()
        
        # Get creation timestamp from registry or fallback to now
        reg_info = self.registry.get_document(doc_id)
        created_at = reg_info["created_at"] if reg_info else now

        return {
            "document_id": doc_id,
            "parser_version": versions.get("metadata", "1.0.0"),
            "graph_version": versions.get("graph", "1.0.0"),
            "chunk_version": versions.get("chunks", "1.0.0"),
            "embedding_version": versions.get("embeddings", "1.0.0"),
            "builder_versions": versions,
            "hashes": hashes,
            "creation_timestamp": created_at,
            "last_updated": now,
            "model_used": self.parser.model
        }
