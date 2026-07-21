# Release Notes (Phase 2C — Production Resilience)

## Major Features
* **Adaptive Rate Limiting**: Dynamic pacing based on rolling request histories instead of static delays.
* **Per-Provider Circuit Breakers**: Standard Closed → Open → Half-Open state transitions supporting recovery detection.
* **Persistent Runtime States**: Observed capacities and stats survive restarts via JSON state files.
* **TTR Tracking**: SRE metric recording duration to recovery after failures.
* **Unified Qualification Gates**: Structured 5-level qualification states with strict Canary evidence thresholds.

## Compatibility & Migrations
* **No Breaking Changes**: v1 APIs are fully frozen and compatible.
