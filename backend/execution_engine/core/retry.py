"""
RetryPolicy — Phase 2C
Classifies exceptions with full failure analysis:
  - Failure Layer (Transport / HTTP / Provider / Schema / Semantic)
  - Root Cause
  - Retry Decision
  - Cooldown Applied
  - Broker Decision

HTTP 429 is NEVER classified as a benchmark failure — it is a quota policy event.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FailureAnalysis:
    """Structured analysis of every failed provider request."""
    failure_layer: str           # Transport | HTTP | Provider | Schema | Semantic
    root_cause: str              # Specific root cause string
    retry_decision: str          # RETRY_BACKOFF | RETRY_OTHER_PROVIDER | WAIT_COOLDOWN | FATAL | NO_RETRY
    cooldown_applied: bool       # Whether a cooldown window should be set
    broker_decision: str         # ROUTE_ELSEWHERE | WAIT | FAIL | NONE
    is_quota_event: bool         # True if 429 — not an engine correctness failure
    retry_after_sec: float = 0.0 # Hint from provider
    details: str = ""


@dataclass
class RetryAction:
    should_retry: bool
    backoff_seconds: float = 0.0
    is_fatal: bool = False
    mark_unavailable: bool = False
    analysis: Optional[FailureAnalysis] = None


class RetryPolicy:
    """
    Centralized retry classification engine.
    Maps execution exceptions to operational policies with full failure analysis.

    CRITICAL: HTTP 429 is distinguished from engine failures.
    """

    @staticmethod
    def classify(exception: Exception) -> RetryAction:
        err_msg = str(exception).lower()
        err_type = type(exception).__name__

        # ------------------------------------------------------------------
        # Import typed exceptions (avoid circular imports)
        # ------------------------------------------------------------------
        try:
            from execution_engine.data_plane.adapters.gemini_client import (
                RateLimitError, TransportError, SchemaError
            )

            # 1. Rate Limit (429) — quota policy, NOT an engine failure
            if isinstance(exception, RateLimitError):
                retry_after = getattr(exception, "retry_after", 0.0)
                return RetryAction(
                    should_retry=True,
                    backoff_seconds=max(retry_after, 10.0),
                    is_fatal=False,
                    mark_unavailable=True,
                    analysis=FailureAnalysis(
                        failure_layer="Provider",
                        root_cause="HTTP_429_QUOTA_EXHAUSTED",
                        retry_decision="WAIT_COOLDOWN",
                        cooldown_applied=True,
                        broker_decision="ROUTE_ELSEWHERE",
                        is_quota_event=True,
                        retry_after_sec=retry_after,
                        details=f"Provider quota reached. Retry-After={retry_after:.0f}s. "
                                "This is a provider policy event, not an engine failure.",
                    ),
                )

            # 2. Transport failure
            if isinstance(exception, TransportError):
                return RetryAction(
                    should_retry=True,
                    backoff_seconds=3.0,
                    is_fatal=False,
                    mark_unavailable=False,
                    analysis=FailureAnalysis(
                        failure_layer="Transport",
                        root_cause="NETWORK_FAILURE",
                        retry_decision="RETRY_BACKOFF",
                        cooldown_applied=False,
                        broker_decision="ROUTE_ELSEWHERE",
                        is_quota_event=False,
                        details=str(exception),
                    ),
                )

            # 3. Schema / JSON failure
            if isinstance(exception, SchemaError):
                return RetryAction(
                    should_retry=True,
                    backoff_seconds=0.0,
                    is_fatal=False,
                    mark_unavailable=False,
                    analysis=FailureAnalysis(
                        failure_layer="Schema",
                        root_cause="JSON_PARSE_FAILURE",
                        retry_decision="RETRY_OTHER_PROVIDER",
                        cooldown_applied=False,
                        broker_decision="ROUTE_ELSEWHERE",
                        is_quota_event=False,
                        details=str(exception),
                    ),
                )

        except ImportError:
            pass

        # ------------------------------------------------------------------
        # String-based classification (fallback)
        # ------------------------------------------------------------------

        # 429 via string
        if "429" in err_msg or "rate limit" in err_msg or "too many requests" in err_msg or "quota" in err_msg:
            return RetryAction(
                should_retry=True,
                backoff_seconds=60.0,
                is_fatal=False,
                mark_unavailable=True,
                analysis=FailureAnalysis(
                    failure_layer="Provider",
                    root_cause="HTTP_429_QUOTA_EXHAUSTED",
                    retry_decision="WAIT_COOLDOWN",
                    cooldown_applied=True,
                    broker_decision="ROUTE_ELSEWHERE",
                    is_quota_event=True,
                    details="429 detected via error string. Provider quota policy event.",
                ),
            )

        # Network / transport
        if any(k in err_msg for k in ("connection", "timeout", "network", "refused", "502", "503", "504")):
            return RetryAction(
                should_retry=True,
                backoff_seconds=3.0,
                is_fatal=False,
                mark_unavailable=False,
                analysis=FailureAnalysis(
                    failure_layer="Transport",
                    root_cause="NETWORK_FAILURE",
                    retry_decision="RETRY_BACKOFF",
                    cooldown_applied=False,
                    broker_decision="ROUTE_ELSEWHERE",
                    is_quota_event=False,
                    details=str(exception),
                ),
            )

        # Schema
        if any(k in err_msg for k in ("malformed json", "jsondecodeerror", "json.decoder", "validationerror", "parse")):
            return RetryAction(
                should_retry=True,
                backoff_seconds=0.0,
                is_fatal=False,
                mark_unavailable=False,
                analysis=FailureAnalysis(
                    failure_layer="Schema",
                    root_cause="JSON_PARSE_FAILURE",
                    retry_decision="RETRY_OTHER_PROVIDER",
                    cooldown_applied=False,
                    broker_decision="ROUTE_ELSEWHERE",
                    is_quota_event=False,
                    details=str(exception),
                ),
            )

        # Safety / blocked
        if any(k in err_msg for k in ("safety", "blocked", "content policy")):
            return RetryAction(
                should_retry=False,
                is_fatal=True,
                analysis=FailureAnalysis(
                    failure_layer="Provider",
                    root_cause="CONTENT_BLOCKED_SAFETY_FILTER",
                    retry_decision="FATAL",
                    cooldown_applied=False,
                    broker_decision="FAIL",
                    is_quota_event=False,
                    details=str(exception),
                ),
            )

        # Auth
        if any(k in err_msg for k in ("auth", "api key", "unauthorized", "invalid key", "403")):
            return RetryAction(
                should_retry=False,
                is_fatal=True,
                mark_unavailable=True,
                analysis=FailureAnalysis(
                    failure_layer="HTTP",
                    root_cause="AUTHENTICATION_FAILURE",
                    retry_decision="FATAL",
                    cooldown_applied=True,
                    broker_decision="FAIL",
                    is_quota_event=False,
                    details=str(exception),
                ),
            )

        # Generic
        return RetryAction(
            should_retry=True,
            backoff_seconds=2.0,
            analysis=FailureAnalysis(
                failure_layer="Provider",
                root_cause="UNKNOWN_PROVIDER_FAILURE",
                retry_decision="RETRY_BACKOFF",
                cooldown_applied=False,
                broker_decision="ROUTE_ELSEWHERE",
                is_quota_event=False,
                details=str(exception),
            ),
        )
