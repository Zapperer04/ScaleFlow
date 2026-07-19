from typing import List
import logging
from execution_engine.control_plane.interfaces import ResourceBroker, CapabilityRegistry
from execution_engine.core.requirements import ProviderRequirements
from execution_engine.data_plane.adapters.base import ResourceProvider
from execution_engine.control_plane.health import ProviderStatusService, ProviderHealthService

class DefaultResourceBroker(ResourceBroker):
    def __init__(
        self, 
        providers: List[ResourceProvider], 
        registry: CapabilityRegistry,
        status_service: ProviderStatusService,
        health_service: ProviderHealthService
    ):
        self.providers = {p.get_provider_id(): p for p in providers}
        self.registry = registry
        self.status = status_service
        self.health = health_service
        self.logger = logging.getLogger("ResourceBroker")

    def _score_provider(self, provider_id: str, requirements: ProviderRequirements) -> int:
        caps = self.registry.get_capabilities(provider_id)
        if requirements.multimodal and not caps.get("supports_images"):
            return -1
        if requirements.streaming and not caps.get("supports_streaming"):
            return -1
        if requirements.context_window > caps.get("max_context", 0):
            return -1
            
        health_score = self.health.get_health_score(provider_id)
        capability_score = 100 
        return (health_score * 0.8) + (capability_score * 0.2)

    def acquire(self, requirements: ProviderRequirements) -> ResourceProvider:
        scored_providers = []
        for pid in self.providers.keys():
            if not self.status.is_available(pid):
                continue
            score = self._score_provider(pid, requirements)
            if score >= 0:
                scored_providers.append((score, pid))
                
        if not scored_providers:
            raise Exception("No capable, available providers found.")
            
        scored_providers.sort(reverse=True)
        best_provider_id = scored_providers[0][1]
        return self.providers[best_provider_id]
