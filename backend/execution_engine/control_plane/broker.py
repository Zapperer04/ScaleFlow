from typing import List, Optional, Tuple
import logging
import time

from execution_engine.control_plane.interfaces import ResourceBroker, CapabilityRegistry
from execution_engine.core.requirements import ProviderRequirements
from execution_engine.data_plane.adapters.base import ResourceProvider
from execution_engine.control_plane.health import ProviderStatusService, ProviderHealthService
from execution_engine.control_plane.circuit_breaker import (
    get_circuit_registry, get_cooldown_scheduler, CircuitState
)
from execution_engine.control_plane.adaptive_rate_manager import get_adaptive_rate_manager


class BrokerDecision:
    """Records every routing decision with full explanation."""

    def __init__(self, selected: Optional[str], candidates: dict, rejected: dict, runner_up: Optional[str] = None, decision_margin: int = 0, selection_reasons: list = None):
        self.selected = selected
        self.candidates = candidates         # provider_id -> score
        self.rejected = rejected             # provider_id -> rejection_reason
        self.runner_up = runner_up
        self.decision_margin = decision_margin
        self.selection_reasons = selection_reasons or []
        self.timestamp = time.time()

    def to_dict(self) -> dict:
        return {
            "selected_provider": self.selected,
            "candidates_scored": self.candidates,
            "providers_rejected": self.rejected,
            "runner_up": self.runner_up,
            "decision_margin": self.decision_margin,
            "selection_reasons": self.selection_reasons,
            "timestamp": round(self.timestamp, 3),
            "iso_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.timestamp)),
        }


class DefaultResourceBroker(ResourceBroker):
    """
    Task 5: Adaptive Broker
    Dynamically avoids providers that are:
    - circuit-breaker OPEN
    - in cooldown
    - quota-exhausted (marked unavailable)
    
    Every routing decision records WHY a provider was rejected.
    Maintains a rolling history of routing decisions.
    """

    MAX_HISTORY = 500

    def __init__(
        self,
        providers: List[ResourceProvider],
        registry: CapabilityRegistry,
        status_service: ProviderStatusService,
        health_service: ProviderHealthService,
    ):
        self.providers = {p.get_provider_id(): p for p in providers}
        self.registry = registry
        self.status = status_service
        self.health = health_service
        self.logger = logging.getLogger("ResourceBroker")
        self._decision_history: List[dict] = []
        get_adaptive_rate_manager().register_broker(self)
    def _score_provider(self, provider_id: str, requirements: ProviderRequirements) -> Tuple[int, str]:
        """
        Returns (score, rejection_reason).
        Score < 0 means the provider is rejected.
        """
        # 1. Capability check
        caps = self.registry.get_capabilities(provider_id)
        if requirements.multimodal and not caps.get("supports_images"):
            return -1, "capability:no_multimodal_support"
        if requirements.streaming and not caps.get("supports_streaming"):
            return -1, "capability:no_streaming_support"
        if requirements.context_window > caps.get("max_context", 0):
            return -1, f"capability:context_window_too_small({caps.get('max_context')})"

        # 2. Circuit breaker check
        cb = get_circuit_registry().get(provider_id)
        if not cb.is_allowed():
            time_left = cb.time_until_open()
            return -1, f"circuit_breaker:OPEN(resets_in={time_left:.0f}s)"

        # 3. Cooldown check
        cooldown_sched = get_cooldown_scheduler()
        if cooldown_sched.is_in_cooldown(provider_id):
            remaining = cooldown_sched.cooldown_remaining(provider_id)
            return -1, f"cooldown:active(remaining={remaining:.0f}s)"

        # 4. Availability check (quota / status service)
        is_avail, avail_reason = self.status.get_availability(provider_id)
        if not is_avail:
            return -1, f"status:unavailable({avail_reason})"

        # 5. Adaptive rate check
        rate_mgr = get_adaptive_rate_manager()
        can_req, wait = rate_mgr.can_request(provider_id)
        if not can_req:
            return -1, f"rate_limit:pacing_gap(wait={wait:.1f}s)"

        # 6. Compute score
        health_score = self.health.get_health_score(provider_id)
        capability_score = 100

        # Quality feedback from shadow history
        import os, json
        quality_score = 1.0
        history_path = "reports/shadow_history.json"
        if os.path.exists(history_path):
            try:
                with open(history_path, "r") as f:
                    history = json.load(f) or []
                provider_runs = [
                    r for r in history
                    if r.get("details", {}).get("provider") == provider_id
                ]
                if provider_runs:
                    quality_score = sum(
                        r.get("details", {}).get("confidence", 1.0) for r in provider_runs
                    ) / len(provider_runs)
            except Exception:
                pass

        # Weight: 50% health, 20% capability, 30% quality
        final_score = (health_score * 0.5) + (capability_score * 0.2) + (quality_score * 100.0 * 0.3)
        return int(final_score), ""

    def acquire(self, requirements: ProviderRequirements) -> ResourceProvider:
        candidates = {}
        rejected = {}

        for pid in self.providers.keys():
            score, reason = self._score_provider(pid, requirements)
            if score >= 0:
                candidates[pid] = score
            else:
                rejected[pid] = reason
                self.logger.info(f"[Broker] Rejected {pid}: {reason}")

        if not candidates:
            decision = BrokerDecision(None, candidates, rejected)
            self._record_decision(decision)
            reasons = "; ".join(f"{p}={r}" for p, r in rejected.items())
            raise Exception(
                f"No capable, available providers found. Rejections: [{reasons}]"
            )

        sorted_cands = sorted(candidates.items(), key=lambda x: x[1], reverse=True)
        best, best_score = sorted_cands[0]
        runner_up = sorted_cands[1][0] if len(sorted_cands) > 1 else None
        runner_up_score = sorted_cands[1][1] if len(sorted_cands) > 1 else 0
        decision_margin = int(best_score - runner_up_score)

        reasons = ["healthy", "quota_available"]
        if best_score > 80:
            reasons.append("high_confidence")

        decision = BrokerDecision(
            best, candidates, rejected,
            runner_up=runner_up,
            decision_margin=decision_margin,
            selection_reasons=reasons
        )

        self.logger.info(f"[Broker] Selected {best} (score={best_score}) from "
                          f"candidates={list(candidates.keys())} rejected={list(rejected.keys())}")

        self._record_decision(decision)
        return self.providers[best]

    def _record_decision(self, decision: BrokerDecision):
        d = decision.to_dict()
        self._decision_history.append(d)
        if len(self._decision_history) > self.MAX_HISTORY:
            self._decision_history = self._decision_history[-self.MAX_HISTORY:]

    def get_routing_history(self) -> list:
        return list(self._decision_history)
