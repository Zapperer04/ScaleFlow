from typing import Dict, Any
from backend.dto.worker import WorkerTaskDTO

class WorkerAdapter:
    @staticmethod
    def legacy_to_dto(legacy_task: Any) -> WorkerTaskDTO:
        if hasattr(legacy_task, "to_dict"):
            data = legacy_task.to_dict()
        else:
            data = dict(legacy_task)
        return WorkerTaskDTO(
            task_id=data["id"],
            task_type=data["type"],
            task_data=data.get("data", {}),
            priority=data.get("priority", "medium"),
            assigned_worker_id=data.get("assigned_worker_id"),
        )

    @staticmethod
    def dto_to_legacy(dto: WorkerTaskDTO) -> Dict[str, Any]:
        return {
            "id": dto.task_id,
            "type": dto.task_type,
            "data": dto.task_data,
            "priority": dto.priority,
            "assigned_worker_id": dto.assigned_worker_id,
        }
