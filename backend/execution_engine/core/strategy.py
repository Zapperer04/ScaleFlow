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
        return {"nodes": [{"id": "legacy-1", "type": "text", "content": "legacy output"}]}

class ExecutionEngineStrategy(ParserStrategy):
    def __init__(self, worker):
        self.worker = worker
        
    def parse(self, job: JobSpec) -> Dict[str, Any]:
        print(f"[ExecutionEngineStrategy] Routing job {job.id} to new worker loop.")
        success = self.worker.execute_job(job, trace_id=f"trace-{job.id}")
        if not success:
            raise Exception("ExecutionEngine failed to process the job.")
        return {"nodes": []}

class StrategyFactory:
    @staticmethod
    def create(strategy_type: str, worker=None) -> ParserStrategy:
        if strategy_type == "execution_engine" and worker:
            return ExecutionEngineStrategy(worker)
        return LegacyStrategy()
