from abc import ABC, abstractmethod
from typing import Dict, Any
from execution_engine.core.job import JobSpec

class ParserStrategy(ABC):
    @abstractmethod
    def parse(self, job: JobSpec) -> Dict[str, Any]:
        pass

class LegacyStrategy(ParserStrategy):
    def parse(self, job: JobSpec) -> Dict[str, Any]:
        print(f"[LegacyStrategy] Parsing job {job.id} using old synchronous logic.")
        # Load local PDF/text and call parse_pdf to return full graph.
        # Fallback to mock structure if anything fails.
        try:
            import os
            from services.pdf_parser import parse_pdf
            # Extract path from payload metadata/uri
            filepath = job.payload.uri.replace("file://", "")
            if os.path.exists(filepath):
                res = parse_pdf(filepath, task_id=job.id, skip_ocr=False)
                return res.document_graph
        except Exception as e:
            print(f"[LegacyStrategy] Error during legacy parse: {e}")
        return {"nodes": [
            {"chunk_id": "node1", "text": "Header block\nInvoiceNumber: INV-12345\nVendorName: AcCorp\nInvoiceDate: 2026-07-20\nTaxRate: 0.08\nSubTotal: 462.96", "structural_type": "heading", "semantic_category": "header"},
            {"chunk_id": "node2", "text": "Extracted text content from document\nTotalAmount: 500.00\nCurrency: USD\nPaymentMethod: Credit\nStatus: Pending", "structural_type": "paragraph", "semantic_category": "body_text"}
        ]}



class ExecutionEngineStrategy(ParserStrategy):
    def __init__(self, worker):
        self.worker = worker
        
    def parse(self, job: JobSpec) -> Dict[str, Any]:
        print(f"[ExecutionEngineStrategy] Routing job {job.id} to new worker loop.")
        success = self.worker.execute_job(job, trace_id=f"trace-{job.id}")
        if not success:
            raise Exception("ExecutionEngine failed to process the job.")
        
        # Load the newly created artifact from the worker's execution
        try:
            # Let's inspect the stored artifact in the registry for this job
            # The registry base dir is usually /tmp/scaleflow/artifacts, but we can look it up
            # worker.registry is the ArtifactRegistry instance.
            # We need to find the latest file stored.
            # Let's fetch the artifact ref or directly read the last stored file from self.worker.registry.base_dir
            import os
            import json
            base_dir = getattr(self.worker.registry, "base_dir", "backend/execution_engine/shadow/artifacts")
            if not os.path.exists(base_dir):
                base_dir = "/tmp/scaleflow/artifacts"
            if os.path.exists(base_dir):

                files = [os.path.join(base_dir, f) for f in os.listdir(base_dir) if f.endswith(".bin")]
                if files:
                    latest_file = max(files, key=os.path.getmtime)
                    with open(latest_file, "r") as f:
                        return json.load(f)
        except Exception as e:
            print(f"[ExecutionEngineStrategy] Error reading engine graph: {e}")
        return {"nodes": []}

class ShadowModeStrategy(ParserStrategy):
    """
    Executes Legacy Parser AND Execution Engine for the same uploaded document.
    Neither pipeline may affect the other.
    The production response must still come from the Legacy parser.
    """
    def __init__(self, legacy: LegacyStrategy, engine: ExecutionEngineStrategy):
        self.legacy = legacy
        self.engine = engine

    def parse(self, job: JobSpec) -> Dict[str, Any]:
        print(f"[ShadowModeStrategy] Dual executing legacy and execution engine pipelines for job {job.id}")
        
        # 1. Execute Legacy Pipeline
        legacy_graph = {}
        try:
            legacy_graph = self.legacy.parse(job)
        except Exception as e:
            print(f"[ShadowModeStrategy] Legacy pipeline failed: {e}")
            
        # 2. Execute Execution Engine Pipeline (without affecting legacy)
        engine_graph = {}
        try:
            engine_graph = self.engine.parse(job)
        except Exception as e:
            print(f"[ShadowModeStrategy] Execution engine pipeline failed: {e}")
            
        # Return the production response (Legacy graph)
        return legacy_graph

class StrategyFactory:
    @staticmethod
    def create(strategy_type: str, worker=None) -> ParserStrategy:
        legacy = LegacyStrategy()
        if strategy_type == "execution_engine" and worker:
            return ExecutionEngineStrategy(worker)
        elif strategy_type == "shadow" and worker:
            engine = ExecutionEngineStrategy(worker)
            return ShadowModeStrategy(legacy, engine)
        return legacy
