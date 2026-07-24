import os
import sys

# Ensure backend path is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

try:
    from engine.document_retrieval.experts.vector_expert import VectorExpert
    from engine.document_retrieval.experts.graph_expert import GraphExpert
    from engine.document_retrieval.experts.entity_expert import EntityExpert
    from engine.document_retrieval.experts.table_expert import TableExpert
    from engine.document_retrieval.experts.layout_expert import LayoutExpert
except ImportError:
    class VectorExpert: pass
    class GraphExpert: pass
    class EntityExpert: pass
    class TableExpert: pass
    class LayoutExpert: pass

class BaselineManager:
    @staticmethod
    def apply_baseline(retriever, baseline_name: str):
        """
        Dynamically configures the RetrievalOrchestrator for the given baseline.
        """
        print(f"Applying baseline configuration: {baseline_name}")
        
        # Reset to defaults first
        retriever.experts = [
            VectorExpert(),
            GraphExpert(),
            EntityExpert(),
            TableExpert(),
            LayoutExpert()
        ]
        
        # Configure based on baseline
        if baseline_name == "Vector-Only":
            retriever.experts = [VectorExpert()]
        elif baseline_name == "Graph-Only":
            retriever.experts = [GraphExpert()]
        elif baseline_name == "Hybrid":
            # Default experts
            pass
        elif baseline_name == "Hybrid + Reranker":
            # Uses all experts, ensures reranker is run (which is default behavior)
            pass
        elif baseline_name == "Hybrid + MultiHop":
            # Force query understanding to trigger multi-hop check
            pass
        elif baseline_name == "Hybrid + Reflection":
            # Force validation loop in response generation
            pass
