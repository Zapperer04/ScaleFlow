from abc import ABC, abstractmethod
from typing import Optional
from execution_engine.core.requirements import ProviderRequirements
from execution_engine.data_plane.adapters.base import ResourceProvider

class QuotaManager(ABC):
    @abstractmethod
    def acquire_quota(self, provider_id: str, cost: int = 1) -> bool:
        pass
    @abstractmethod
    def release_quota(self, provider_id: str, cost: int = 1) -> None:
        pass

class LeaseManager(ABC):
    @abstractmethod
    def acquire_lease(self, job_id: str, ttl_seconds: int = 300) -> Optional[str]:
        pass
    @abstractmethod
    def release_lease(self, job_id: str, lease_id: str) -> bool:
        pass
        
class CapabilityRegistry(ABC):
    @abstractmethod
    def register_provider(self, provider_id: str, capabilities: dict) -> None:
        pass
    @abstractmethod
    def get_capabilities(self, provider_id: str) -> dict:
        pass

class ResourceBroker(ABC):
    @abstractmethod
    def acquire(self, requirements: ProviderRequirements) -> ResourceProvider:
        pass
