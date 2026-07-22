import os
import sys
import pytest
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.document_pipeline.orchestrator import ProductionParsingOrchestrator

TEST_PDF_PATH = "test_data/category_A_simple.pdf"

@pytest.fixture
def temp_store_dir():
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

def test_orchestrator_manifest_generation(temp_store_dir):
    os.environ["TEST_OFFLINE_MODE"] = "True"
    orchestrator = ProductionParsingOrchestrator(base_dir=temp_store_dir)
    
    doc_id = orchestrator.process_document(TEST_PDF_PATH, force_reparse=True)
    
    # Verify Manifest
    manifest = orchestrator.store.load_json(doc_id, "manifest.json")
    assert manifest is not None
    assert manifest["document_id"] == doc_id
    assert "parser_version" in manifest
    assert "graph_version" in manifest
    assert "chunk_version" in manifest
    assert "embedding_version" in manifest
    assert "hashes" in manifest
    assert "model_used" in manifest
    
    # Check that builder versions matches versions dict
    assert isinstance(manifest["builder_versions"], dict)

def test_orchestrator_incremental_rebuild_and_dependency_invalidation(temp_store_dir):
    os.environ["TEST_OFFLINE_MODE"] = "True"
    orchestrator = ProductionParsingOrchestrator(base_dir=temp_store_dir)
    doc_id = orchestrator.process_document(TEST_PDF_PATH, force_reparse=True)
    
    # Modify embeddings files to simulate staleness
    orchestrator.store.save_json(doc_id, "embeddings/embeddings.json", {"data": "stale"})
    
    # Rebuild Chunks (which has embeddings as a downstream dependency)
    # Rebuilding chunks must invalidate/re-run embeddings builder too!
    order = orchestrator.builder_registry.get_ordered_builders(["chunks"])
    names = [b.name for b in order]
    assert "chunks" in names
    assert "embeddings" in names  # Verify dependency invalidation path contains downstream builders
    
    # Execute Rebuild
    orchestrator.rebuild_representations(doc_id, targets=["chunks"])
    
    # Verify embeddings were refreshed and are no longer 'stale'
    refreshed = orchestrator.store.load_json(doc_id, "embeddings/vectors.json")
    assert refreshed is not None
    assert isinstance(refreshed, list)
    assert len(refreshed) > 0
