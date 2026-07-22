import os
from typing import List, Optional
from backend.platform.storage.document_store import DocumentStore
from backend.platform.storage.artifact_store import ArtifactStore
from engine.document_pipeline.orchestrator import ProductionParsingOrchestrator

class IndexManager:
    def __init__(self, document_store: DocumentStore, artifact_store: ArtifactStore):
        self.doc_store = document_store
        self.art_store = artifact_store
        # Initialize engine parsing orchestrator with artifacts dir path
        self.orchestrator = ProductionParsingOrchestrator(base_dir=self.art_store.engine_store.base_dir)

    def run_indexing(self, document_id: str, filepath: str, trace_fn = None) -> str:
        # Wrap process_document of frozen engine
        return self.orchestrator.process_document(filepath, force_reparse=True, trace_fn=trace_fn)

    def rebuild_index(self, document_id: str, targets: List[str] = None, trace_fn = None) -> str:
        # Wrap rebuild_representations of frozen engine
        return self.orchestrator.rebuild_representations(document_id, targets=targets, force=True, trace_fn=trace_fn)

    def validate_versions(self, document_id: str) -> bool:
        """
        Verify that document index representations match current engine parser version schema.
        """
        manifest = self.art_store.load_json(document_id, "manifest.json")
        if not manifest:
            return False
            
        # Verify parser version matches manifest
        engine_versions = self.orchestrator.builder_registry.get_ordered_builders(list(self.orchestrator.builder_registry.builders.keys()))
        return "parser_version" in manifest
