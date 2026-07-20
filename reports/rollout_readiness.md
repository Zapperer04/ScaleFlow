# Rollout Readiness Decision Report

Generated: 2026-07-20T11:30:43Z

## Summary Metrics
- **Total Test Cases**: 1
- **Passing Test Cases**: 0
- **Parity Success Rate**: 0.0%
- **Decomposed Rollout Confidence**: 20.0%

## Rollout Status
**DECISION**: `NOT READY`

### Rollout Confidence Reasons
- Structural mismatches detected on one or more files.
- Semantic matches fall below policy threshold limit.
- Replay validation deterministic; zero lease leaks/duplicate executions.
- Real provider testing pending (15 RPM pacing checks required).

### Strict Validation Checklist
- [ ] Structural Parity >= policy threshold for all documents
- [ ] Semantic Parity >= policy threshold for all documents
- [x] Zero duplicate executions verified
- [x] Zero lease leaks verified
- [x] Zero scheduler-induced 429 rate limit triggers verified
- [x] Replay validation passed

> [!WARNING]
> Rollout is capped at **READY FOR SHADOW**. Live API limits (15 RPM Gemini free tier pacing) and multi-key broker rules must be confirmed on production credentials before migrating to staging or production increments (e.g., 5%, 25%, 100%).

## Rollout Threshold Matrix
- **READY FOR SHADOW**: 100% of test cases pass structural/text/semantic parity thresholds >= policy under local mock loop.
- **READY FOR 5% / 25% / 50% / 100%**: Requires live Gemini/OpenRouter endpoint verification, multi-account key pacing, and schema compatibility checks.
- **NOT READY**: Failed one or more strict check items.
