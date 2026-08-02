import hashlib
import json

class EvaluationDataset:
    def __init__(self):
        self.dataset_name = "ScaleFlow RAG Production Benchmark"
        self.dataset_version = "1.0.0"
        self.created_at = "2026-08-02T15:00:00Z"
        
        # Define Ground Truth QA Pairs
        self.qa_pairs = [
            {
                "id": "q1",
                "question": "What is the primary role of the Replay Engine in ScaleFlow?",
                "expected_answer": (
                    "The Replay Engine is responsible for capturing task execution histories "
                    "and reproducing specific execution states for analysis, debugging, and time-travel debugging."
                ),
                "expected_citations": ["replay.py", "task_registry.py"],
                "expected_chunks": ["chunk_replay_001", "chunk_replay_002"],
                "golden_graph_paths": ["ReplayEngine -> Captures -> TaskHistory", "TaskHistory -> Replays -> ExecutionState"]
            },
            {
                "id": "q2",
                "question": "How does the Scheduling Advisor optimize task allocation?",
                "expected_answer": (
                    "The Scheduling Advisor analyzes performance analytics and execution forecasting "
                    "to recommend optimal worker schedules, balancing execution load and meeting SLAs."
                ),
                "expected_citations": ["adaptive_scheduler.py", "execution_forecaster.py"],
                "expected_chunks": ["chunk_scheduler_001", "chunk_scheduler_002"],
                "golden_graph_paths": ["SchedulingAdvisor -> Consults -> Forecasting", "SchedulingAdvisor -> Allocates -> Workers"]
            },
            {
                "id": "q3",
                "question": "What parameters are configured in the Graph RAG pipeline?",
                "expected_answer": (
                    "The Graph RAG pipeline configures embedding models, chunk size, overlap, graph depth, "
                    "retrievers, and cross-encoders to query and fuse information from documents."
                ),
                "expected_citations": ["rag_pipeline.py", "graph_retriever.py"],
                "expected_chunks": ["chunk_rag_001", "chunk_rag_002"],
                "golden_graph_paths": ["GraphRAG -> Configures -> ChunkSize", "GraphRAG -> Runs -> HybridRetrieval"]
            }
        ]

        # Calculate a deterministic dataset hash
        raw_str = json.dumps(self.qa_pairs, sort_keys=True)
        self.dataset_hash = hashlib.sha256(raw_str.encode("utf-8")).hexdigest()[:16]

    def get_dataset_metadata(self) -> dict:
        """Returns versioning and identifier metadata for the dataset"""
        return {
            "dataset_name": self.dataset_name,
            "dataset_version": self.dataset_version,
            "dataset_hash": self.dataset_hash,
            "created_at": self.created_at
        }

    def get_qa_pairs(self) -> list:
        """Returns the list of ground truth QA pairs"""
        return self.qa_pairs

evaluation_dataset = EvaluationDataset()
