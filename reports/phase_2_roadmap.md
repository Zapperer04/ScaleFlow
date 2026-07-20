# Phase 2 — Production Shadow & Live Validation Roadmap

This document outlines the transition plan to move the ScaleFlow Resource Execution Engine from Phase 1D (Simulation & Parity Verification) to Phase 2 (Production Shadow & Live Validation).

---

## 1. Objectives

1. **Live Provider Integrations**: Transition from simulated endpoints to real API endpoints for Gemini (Google Vertex AI) and OpenRouter (routing to Claude, Mistral, and paid Vision models).
2. **Quota & Rate-Limit Testing**: Verify the default scheduler and resource broker behaviour under real 15 RPM/pacing thresholds for free keys.
3. **Continuous Production Shadowing**: Route actual document uploads from the upload workflow asynchronously to the Execution Engine.
4. **Historical Trend Dashboards**: Monitor 30-day structural/semantic parity stability, provider latency percentiles (P50, P90, P99), and standard deviation.

---

## 2. Deliverables & Milestones

### Milestone 2.1: Live Adapter Deployment
* Implement live client providers for Gemini (Vertex API) and OpenRouter with API key authentication.
* Inject failure conditions (HTTP 429 Rate Limits, malformed stream JSON fragments) to verify rescheduling reliability.

### Milestone 2.2: Dual Production Upload Shadowing
* Wire the upload hook (`frontend/src/components/workspace/upload/useUpload.js`) to trigger dual-parsing.
* Ensure all user uploads are parsed in the background using the Execution Engine alongside the legacy synchronous parsing process.

### Milestone 2.3: Lifecycle Golden Approval Merge UI
* Create a simple human-in-the-loop review workflow within the workspace panel.
* Allow developers to review staged differences (`candidate_delta.json`) and click "Approve and Merge Candidate Graph" to promote graphs to the golden dataset.

---

## 3. Production Rollout Matrix

The promotion matrix governs staging and production traffic shifts:

| Stage | Target Shift | Entry Criteria | Gate Checks |
| :--- | :--- | :--- | :--- |
| **Shadow Mode** | 0% (Asynchronous) | Policy thresholds configured | Comparator stages difference logs |
| **Incremental Staging** | 5% | 100% Shadow pass rate | Zero duplicate executions, zero lease leaks |
| **Canary Shift** | 25% | 7 days error-free staging | Average structural parity stable at >= 99% |
| **Incremental Rollout** | 50% | Successful canary validation | Latency percentiles (P90) <= legacy parsing |
| **Production Target** | 100% | Final architect approval | Deprecation of legacy parser code |
