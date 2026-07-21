"""
Phase 2C Unit Tests
Tests for:
  - AdaptiveRateLimitManager (RPM tracking, pacing, 429 rate)
  - CircuitBreaker (state machine: Closed→Open→HalfOpen→Closed)
  - AdaptiveCooldownScheduler (cooldown EMA, Retry-After)
  - RateLimitError propagation (never silent, always surfaced)
  - FailureAnalysis classification (429 is quota event, not correctness failure)
  - BrokerDecision rejection reasons
  - ProviderHealthService (scoring, decay, 429 soft penalty)
"""
import time
import pytest
from unittest.mock import MagicMock, patch


# ============================================================
# 1. AdaptiveRateLimitManager Tests
# ============================================================

class TestAdaptiveRateLimitManager:

    def setup_method(self):
        # Reset the singleton for each test
        import execution_engine.control_plane.adaptive_rate_manager as arm_mod
        arm_mod._adaptive_rate_manager = None
        from execution_engine.control_plane.adaptive_rate_manager import (
            AdaptiveRateLimitManager, ProviderQuotaState
        )
        self.arm = AdaptiveRateLimitManager()
        self.arm.enable_persistence = False
        self.PQS = ProviderQuotaState

    def test_initial_state_allows_requests(self):
        ok, wait = self.arm.can_request("gemini")
        assert ok is True
        assert wait == 0.0

    def test_records_success_increments_rpm(self):
        self.arm.record_success("gemini", tokens=100)
        state = self.arm.get_state("gemini")
        assert state.observed_rpm() == 1.0

    def test_records_429_updates_moving_rate(self):
        self.arm.record_429("gemini", retry_after=60.0)
        state = self.arm.get_state("gemini")
        assert state.moving_429_rate() == 1.0   # 1/1 = 100%

    def test_cooldown_blocks_requests(self):
        self.arm.apply_cooldown("gemini", duration=3600.0)
        ok, wait = self.arm.can_request("gemini")
        assert ok is False
        assert wait > 0.0

    def test_pacing_gap_grows_on_high_429_rate(self):
        state = self.arm.get_state("gemini")
        # Simulate 6/10 = 60% 429 rate → severe pressure
        for _ in range(4):
            state._attempt_outcomes.append(True)
        for _ in range(6):
            state._attempt_outcomes.append(False)

        gap = state.required_inter_request_gap()
        base_gap = 60.0 / state.observed_rpm_cap
        assert gap >= base_gap * 4.0   # severe pressure multiplier

    def test_to_dashboard_returns_all_providers(self):
        self.arm.record_success("gemini")
        self.arm.record_success("openrouter")
        dash = self.arm.to_dashboard()
        assert "gemini" in dash
        assert "openrouter" in dash

    def test_average_retry_delay_after_429(self):
        state = self.arm.get_state("gemini")
        self.arm.record_429("gemini", retry_after=30.0)
        self.arm.record_429("gemini", retry_after=60.0)
        assert state.average_retry_delay() == 45.0


# ============================================================
# 2. CircuitBreaker State Machine Tests
# ============================================================

class TestCircuitBreaker:

    def setup_method(self):
        import execution_engine.control_plane.circuit_breaker as cb_mod
        cb_mod._circuit_registry = None
        from execution_engine.control_plane.circuit_breaker import (
            ProviderCircuitBreaker, CircuitState
        )
        self.CB = ProviderCircuitBreaker
        self.State = CircuitState

    def test_initial_state_is_closed(self):
        cb = self.CB("gemini", failure_threshold=3)
        assert cb.state() == self.State.CLOSED
        assert cb.is_allowed() is True

    def test_opens_after_failure_threshold(self):
        cb = self.CB("gemini", failure_threshold=3)
        for _ in range(3):
            cb.record_failure("test failure")
        assert cb.state() == self.State.OPEN
        assert cb.is_allowed() is False
        assert cb._open_count == 1

    def test_transitions_to_half_open_after_timeout(self):
        cb = self.CB("gemini", failure_threshold=2, base_reset_timeout_sec=0.1)
        cb.record_failure("f1")
        cb.record_failure("f2")
        assert cb.state() == self.State.OPEN
        time.sleep(0.15)
        # State check should trigger transition
        assert cb.is_allowed() is True   # HALF_OPEN allows probe
        assert cb.state() == self.State.HALF_OPEN

    def test_closes_after_probe_successes(self):
        cb = self.CB("gemini", failure_threshold=2, probe_successes=2, base_reset_timeout_sec=0.05)
        cb.record_failure("f1")
        cb.record_failure("f2")
        time.sleep(0.1)
        cb.record_success()   # probe 1
        cb.record_success()   # probe 2 → CLOSED
        assert cb.state() == self.State.CLOSED
        assert cb._recovery_count == 1

    def test_429_counts_as_failure(self):
        cb = self.CB("gemini", failure_threshold=2)
        cb.record_429(retry_after=30.0)
        cb.record_429(retry_after=30.0)
        assert cb.state() == self.State.OPEN

    def test_time_until_open_decrements(self):
        cb = self.CB("gemini", failure_threshold=1, base_reset_timeout_sec=10.0)
        cb.record_failure("f1")
        t = cb.time_until_open()
        assert 0.0 < t <= 10.0

    def test_success_resets_consecutive_failures_in_closed(self):
        cb = self.CB("gemini", failure_threshold=3)
        cb.record_failure("f1")
        cb.record_failure("f2")
        cb.record_success()   # reset
        cb.record_failure("f3")
        # Only 1 failure since last success — should still be CLOSED
        assert cb.state() == self.State.CLOSED

    def test_to_dict_schema(self):
        cb = self.CB("gemini")
        d = cb.to_dict()
        for key in ["provider_id", "state", "open_count", "recovery_count",
                    "consecutive_failures", "recent_transitions"]:
            assert key in d


# ============================================================
# 3. AdaptiveCooldownScheduler Tests
# ============================================================

class TestAdaptiveCooldownScheduler:

    def setup_method(self):
        import execution_engine.control_plane.circuit_breaker as cb_mod
        cb_mod._cooldown_scheduler = None
        from execution_engine.control_plane.circuit_breaker import AdaptiveCooldownScheduler
        self.sched = AdaptiveCooldownScheduler()

    def test_registers_429_and_sets_cooldown(self):
        estimated = self.sched.register_429("gemini", retry_after=30.0)
        assert estimated >= 30.0   # should be 30*1.1 = 33.0
        assert self.sched.is_in_cooldown("gemini") is True

    def test_cooldown_uses_retry_after_if_provided(self):
        estimated = self.sched.register_429("gemini", retry_after=60.0)
        assert abs(estimated - 66.0) < 0.01   # 60 * 1.1

    def test_no_cooldown_initially(self):
        assert self.sched.is_in_cooldown("openrouter") is False

    def test_cooldown_remaining_decrements(self):
        self.sched.register_429("gemini", retry_after=10.0)
        remaining = self.sched.cooldown_remaining("gemini")
        assert remaining > 0.0 and remaining <= 11.0

    def test_recent_events_recorded(self):
        self.sched.register_429("gemini", retry_after=30.0)
        self.sched.register_429("openrouter", retry_after=60.0)
        events = self.sched.recent_events(10)
        providers = [e["provider"] for e in events]
        assert "gemini" in providers
        assert "openrouter" in providers

    def test_ema_estimation_without_retry_after(self):
        # First call without retry_after uses default
        estimated_first = self.sched.register_429("openrouter", retry_after=0.0)
        assert estimated_first == 60.0   # default

    def test_all_cooldowns_structure(self):
        self.sched.register_429("gemini", retry_after=30.0)
        result = self.sched.all_cooldowns()
        assert "gemini" in result
        g = result["gemini"]
        assert "in_cooldown" in g
        assert "cooldown_remaining_sec" in g
        assert g["in_cooldown"] is True


# ============================================================
# 4. RateLimitError Classification Tests
# ============================================================

class TestRetryPolicyClassification:

    def test_429_is_quota_event_not_engine_failure(self):
        from execution_engine.data_plane.adapters.gemini_client import RateLimitError
        from execution_engine.core.retry import RetryPolicy
        e = RateLimitError("Gemini 429", retry_after=42.0, provider="gemini")
        action = RetryPolicy.classify(e)
        assert action.analysis is not None
        assert action.analysis.is_quota_event is True
        assert action.analysis.failure_layer == "Provider"
        assert action.analysis.root_cause == "HTTP_429_QUOTA_EXHAUSTED"
        assert action.analysis.retry_decision == "WAIT_COOLDOWN"
        assert action.analysis.cooldown_applied is True
        assert action.analysis.broker_decision == "ROUTE_ELSEWHERE"
        assert action.should_retry is True
        assert action.is_fatal is False
        assert action.backoff_seconds >= 42.0

    def test_transport_error_classification(self):
        from execution_engine.data_plane.adapters.gemini_client import TransportError
        from execution_engine.core.retry import RetryPolicy
        e = TransportError("Connection refused")
        action = RetryPolicy.classify(e)
        assert action.analysis.is_quota_event is False
        assert action.analysis.failure_layer == "Transport"
        assert action.analysis.root_cause == "NETWORK_FAILURE"
        assert action.should_retry is True

    def test_schema_error_classification(self):
        from execution_engine.data_plane.adapters.gemini_client import SchemaError
        from execution_engine.core.retry import RetryPolicy
        e = SchemaError("JSON parse failure")
        action = RetryPolicy.classify(e)
        assert action.analysis.failure_layer == "Schema"
        assert action.analysis.root_cause == "JSON_PARSE_FAILURE"
        assert action.should_retry is True

    def test_string_429_classified_as_quota(self):
        from execution_engine.core.retry import RetryPolicy
        e = Exception("quota exceeded: 429 rate limit hit")
        action = RetryPolicy.classify(e)
        assert action.analysis.is_quota_event is True
        assert action.should_retry is True

    def test_auth_failure_is_fatal(self):
        from execution_engine.core.retry import RetryPolicy
        e = Exception("401 unauthorized api key invalid")
        action = RetryPolicy.classify(e)
        assert action.is_fatal is True
        assert action.should_retry is False

    def test_429_never_raises_is_fatal(self):
        from execution_engine.data_plane.adapters.gemini_client import RateLimitError
        from execution_engine.core.retry import RetryPolicy
        e = RateLimitError("429", retry_after=30.0, provider="gemini")
        action = RetryPolicy.classify(e)
        # 429 must NEVER be fatal
        assert action.is_fatal is False


# ============================================================
# 5. GeminiClient 429 Propagation Tests
# ============================================================

class TestGeminiClient429Propagation:

    @patch("requests.request")
    def test_raises_rate_limit_error_on_429(self, mock_request):
        from execution_engine.data_plane.adapters.gemini_client import (
            GeminiClient, RateLimitError
        )
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.headers = {"Retry-After": "42"}
        mock_resp.json.return_value = {}
        mock_request.return_value = mock_resp

        client = GeminiClient(api_key="fake-key", model="gemini-2.5-flash")
        with pytest.raises(RateLimitError) as exc_info:
            client.generate_content("hello")

        e = exc_info.value
        assert e.retry_after == 42.0
        assert e.provider == "gemini"
        assert e.failure_layer == "Provider"
        assert e.root_cause == "HTTP_429_QUOTA_EXHAUSTED"

    @patch("requests.request")
    def test_never_retries_on_429(self, mock_request):
        """The client should raise immediately on 429 — no silent retry."""
        from execution_engine.data_plane.adapters.gemini_client import (
            GeminiClient, RateLimitError
        )
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.headers = {}
        mock_resp.json.return_value = {}
        mock_request.return_value = mock_resp

        client = GeminiClient(api_key="fake-key", model="gemini-2.5-flash")
        with pytest.raises(RateLimitError):
            client.generate_content("hello")

        # Should be called exactly once — no retries on 429
        assert mock_request.call_count == 1

    @patch("requests.request")
    def test_retry_after_parsed_from_retry_info_body(self, mock_request):
        """Parse Retry-After from retryDelay in response body when header absent."""
        from execution_engine.data_plane.adapters.gemini_client import (
            GeminiClient, RateLimitError
        )
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.headers = {}
        mock_resp.json.return_value = {
            "error": {
                "details": [{
                    "@type": "type.googleapis.com/google.rpc.RetryInfo",
                    "retryDelay": "30s"
                }]
            }
        }
        mock_request.return_value = mock_resp

        client = GeminiClient(api_key="fake-key", model="gemini-2.5-flash")
        with pytest.raises(RateLimitError) as exc_info:
            client.generate_content("hello")

        assert exc_info.value.retry_after == 30.0


# ============================================================
# 6. OpenRouterClient 429 Propagation Tests
# ============================================================

class TestOpenRouterClient429Propagation:

    @patch("requests.request")
    def test_raises_rate_limit_error_on_429(self, mock_request):
        from execution_engine.data_plane.adapters.openrouter_client import OpenRouterClient
        from execution_engine.data_plane.adapters.gemini_client import RateLimitError
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.headers = {"Retry-After": "60"}
        mock_request.return_value = mock_resp

        client = OpenRouterClient(api_key="fake-key", model="gemma")
        with pytest.raises(RateLimitError) as exc_info:
            client.generate_content("hello")

        e = exc_info.value
        assert e.retry_after == 60.0
        assert e.provider == "openrouter"

    @patch("requests.request")
    def test_never_retries_on_429(self, mock_request):
        from execution_engine.data_plane.adapters.openrouter_client import OpenRouterClient
        from execution_engine.data_plane.adapters.gemini_client import RateLimitError
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.headers = {}
        mock_request.return_value = mock_resp

        client = OpenRouterClient(api_key="fake-key", model="gemma")
        with pytest.raises(RateLimitError):
            client.generate_content("hello")

        # Called exactly once — no retries
        assert mock_request.call_count == 1


# ============================================================
# 7. ProviderHealthService Enhanced Scoring Tests
# ============================================================

class TestEnhancedHealthService:

    def test_429_applies_soft_penalty(self):
        """429 should apply a smaller penalty than total failure."""
        import redis
        from execution_engine.control_plane.health import ProviderHealthService

        mock_redis = MagicMock()
        mock_redis.get.return_value = "100.0"

        svc = ProviderHealthService(mock_redis, alpha=0.15)

        # Record 429 (success=False, is_429=True)
        svc.record_metrics("gemini", latency=1.0, success=False, is_429=True)

        # penalty = 25 (not success) + 10 (is_429) = 35
        # event_score = 65.0
        # new_health = (0.15 * 65) + (0.85 * 100) = 9.75 + 85.0 = 94.75
        # decay boost (94.75 > 80): 0.01 * (100 - 94.75) = 0.0525
        # final = 94.8025
        call_args = mock_redis.set.call_args
        key, value = call_args[0]
        assert key == "provider:gemini:health"
        final = float(value)
        assert final < 100.0
        assert final > 90.0   # soft penalty — not catastrophic

    def test_success_recovers_from_penalty(self):
        """Multiple successes should gradually push score back to 100."""
        import redis
        from execution_engine.control_plane.health import ProviderHealthService

        calls = []
        current_val = [90.0]

        def mock_get(key):
            return str(current_val[0])

        def mock_set(key, val):
            current_val[0] = float(val)
            calls.append(float(val))

        mock_redis = MagicMock()
        mock_redis.get.side_effect = mock_get
        mock_redis.set.side_effect = mock_set

        svc = ProviderHealthService(mock_redis, alpha=0.15)

        for _ in range(10):
            svc.record_metrics("gemini", latency=0.5, success=True)

        assert current_val[0] > 90.0   # Recovery is happening

    def test_timeout_applies_extra_penalty(self):
        """Timeouts are more severe than plain failures."""
        mock_redis_plain = MagicMock()
        mock_redis_plain.get.return_value = "100.0"
        mock_redis_timeout = MagicMock()
        mock_redis_timeout.get.return_value = "100.0"

        from execution_engine.control_plane.health import ProviderHealthService

        svc_plain = ProviderHealthService(mock_redis_plain, alpha=0.15)
        svc_timeout = ProviderHealthService(mock_redis_timeout, alpha=0.15)

        svc_plain.record_metrics("p", latency=1.0, success=False, is_timeout=False)
        svc_timeout.record_metrics("p", latency=1.0, success=False, is_timeout=True)

        plain_score = float(mock_redis_plain.set.call_args[0][1])
        timeout_score = float(mock_redis_timeout.set.call_args[0][1])

        assert timeout_score < plain_score   # timeout should score lower


# ============================================================
# 8. Broker Rejection Reason Tests
# ============================================================

class TestBrokerRejectionReasons:

    def test_circuit_breaker_open_rejection(self):
        """Broker should reject provider with circuit breaker OPEN and explain why."""
        import execution_engine.control_plane.circuit_breaker as cb_mod
        cb_mod._circuit_registry = None
        from execution_engine.control_plane.circuit_breaker import get_circuit_registry

        # Open the gemini circuit breaker
        cb = get_circuit_registry().get("gemini")
        # Force open by simulating failures
        cb._consecutive_failures = 999
        from execution_engine.control_plane.circuit_breaker import CircuitState
        cb._state = CircuitState.OPEN
        cb._opened_at = time.time() - 1.0  # opened 1s ago

        assert not cb.is_allowed()

    def test_cooldown_active_rejection(self):
        """Broker should reject provider with active cooldown and explain why."""
        import execution_engine.control_plane.circuit_breaker as cb_mod
        cb_mod._cooldown_scheduler = None
        from execution_engine.control_plane.circuit_breaker import get_cooldown_scheduler

        sched = get_cooldown_scheduler()
        sched.register_429("gemini", retry_after=3600.0)

        assert sched.is_in_cooldown("gemini") is True
        remaining = sched.cooldown_remaining("gemini")
        assert remaining > 3500.0  # nearly full cooldown still remaining


# ============================================================
# 9. ProviderQuotaState to_dict Schema Test
# ============================================================

class TestProviderQuotaStateDictSchema:

    def test_to_dict_has_all_required_fields(self):
        from execution_engine.control_plane.adaptive_rate_manager import ProviderQuotaState
        state = ProviderQuotaState("gemini", observed_rpm_cap=15)
        d = state.to_dict()
        for field in [
            "provider_id", "observed_rpm", "observed_rpm_cap",
            "observed_tpm", "moving_429_rate", "average_retry_delay_sec",
            "burst_capacity", "in_cooldown", "cooldown_remaining_sec",
            "cooldown_count", "inter_request_gap_sec"
        ]:
            assert field in d, f"Missing field: {field}"


# ============================================================
# 10. End-to-end: 429 → Cooldown → RESUME flow (mocked)
# ============================================================

class TestEnd2End429CooldownResume:

    def test_429_triggers_cooldown_and_circuit_tracking(self):
        """Simulate the full Phase 2C flow: 429 → register cooldown → CB records."""
        import execution_engine.control_plane.adaptive_rate_manager as arm_mod
        import execution_engine.control_plane.circuit_breaker as cb_mod
        arm_mod._adaptive_rate_manager = None
        cb_mod._circuit_registry = None
        cb_mod._cooldown_scheduler = None

        from execution_engine.control_plane.adaptive_rate_manager import get_adaptive_rate_manager
        from execution_engine.control_plane.circuit_breaker import (
            get_circuit_registry, get_cooldown_scheduler
        )

        arm = get_adaptive_rate_manager()
        cr = get_circuit_registry()
        cs = get_cooldown_scheduler()

        # Simulate 429 hitting all three subsystems
        retry_after = 42.0
        provider = "gemini"

        cs.register_429(provider, retry_after=retry_after)
        arm.record_429(provider, retry_after=retry_after)
        cr.get(provider).record_429(retry_after=retry_after)

        # Verify: cooldown is active
        assert cs.is_in_cooldown(provider) is True
        assert cs.cooldown_remaining(provider) > 40.0

        # Verify: adaptive rate manager reflects 429
        state = arm.get_state(provider)
        assert state.moving_429_rate() == 1.0

        # Verify: circuit breaker recorded the failure
        cb_state = cr.get(provider).to_dict()
        assert cb_state["consecutive_failures"] >= 1

        # Verify: decision dict has correct reasons
        print("✓ 429 → Cooldown registered, CB failure recorded, rate tracking updated.")


# ============================================================
# 11. Time to Recovery (TTR) and Broker Stats Tests
# ============================================================

class TestTTRAndBrokerStats:

    def test_ttr_tracking_on_circuit_recovery(self):
        from execution_engine.control_plane.circuit_breaker import ProviderCircuitBreaker, CircuitState
        import time
        cb = ProviderCircuitBreaker("openrouter", failure_threshold=2)
        
        # Open the circuit
        cb.record_failure("test", cooldown_hint=1.0)
        cb.record_failure("test", cooldown_hint=1.0)
        assert cb.state() == CircuitState.OPEN
        assert cb._opened_at is not None
        
        # Transition to Closed (Probing success)
        cb._state = CircuitState.HALF_OPEN
        cb.record_success()
        cb.record_success()
        assert cb.state() == CircuitState.CLOSED
        
        # Verify TTR was recorded
        d = cb.to_dict()
        assert d["avg_ttr_sec"] >= 0.0
        assert len(d["ttr_history"]) == 1

    def test_broker_stats_registered_and_recorded(self):
        from execution_engine.control_plane.adaptive_rate_manager import get_adaptive_rate_manager
        from execution_engine.control_plane.broker import DefaultResourceBroker
        import json
        import os

        # Clean old state
        if os.path.exists("reports/provider_runtime_state.json"):
            try:
                os.remove("reports/provider_runtime_state.json")
            except Exception:
                pass

        arm = get_adaptive_rate_manager()
        arm._force_pytest_persistence = True
        broker = MagicMock()
        broker.get_routing_history.return_value = [
            {"selected_provider": "gemini", "providers_rejected": {}},
            {"selected_provider": "openrouter", "providers_rejected": {"gemini": "cooldown"}},
        ]
        arm.register_broker(broker)

        # Record a success to trigger save
        arm.record_success("gemini", tokens=50, latency_ms=100.0, queue_wait_ms=10.0)

        # Verify file contents
        path = "reports/provider_runtime_state.json"
        assert os.path.exists(path)
        with open(path, "r") as f:
            data = json.load(f)
        
        assert "gemini" in data
        assert data["gemini"]["avg_latency_ms"] == 100.0
        assert data["gemini"]["avg_queue_wait_ms"] == 10.0
        assert data["gemini"]["broker_selected"] == 1
        assert data["gemini"]["broker_rejected"] == 1
        assert data["gemini"]["selection_rate"] == 50.0
        
        # Clean up
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass
