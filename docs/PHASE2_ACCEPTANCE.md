# Phase 2 Acceptance Criteria & Contract

This document serves as the formal contract defining the exit criteria, SLO targets, promotion/rollback policies, and the required qualification evidence to declare Phase 2 successful.

---

## 1. Exit Criteria

Phase 2 is considered complete when the following conditions are satisfied:

| Metric | Target | Verification Method |
| :--- | :--- | :--- |
| **System Correctness** | 100% lease-leak and duplicate-execution free | Shadow Run Audit logs |
| **Deterministic Replay** | 100% parity on repeated execution graphs | Replay Runner check |
| **Shadow Parity** | $\ge$ 99% structural and text parity, $\ge$ 60% semantic parity | Shadow Comparator Pipeline |
| **Operational SLOs** | All latency and reliability target thresholds met | Provider Metrics Report |
| **Canary Rollout** | Canary phase (5% traffic) active and error-free for $\ge$ 48h | Rollout controller logs |

---

## 2. Production SLO Targets

- **No-Retry Execution Rate**: $\ge$ 99% of documents processed without experiencing recoverable provider errors.
- **Lease Release Reliability**: $\ge$ 99.9% of leases successfully released after job completion.
- **Latency Target**: 95% of documents processed and completed within 120 seconds.

---

## 3. Promotion & Rollback Rules

### Promotion Progression
Promotion follows a stepped progression:
$$0\% \text{ (Shadow)} \rightarrow 5\% \rightarrow 10\% \rightarrow 25\% \rightarrow 50\% \rightarrow 100\%$$

- **Stability Window**: A promotion to the next tier requires sustaining target parity and SLOs for a minimum of 48 hours (or 20 test runs during qualification phases) with a minimum of 50 documents processed.
- **Quality vs. Correctness Gating**: Only Correctness failures (lease leaks, duplicate execution, 429 errors) block promotion. Minor fluctuations in provider quality (confidence $\pm 2\%$) do not gate rollout if within threshold bounds.

### Rollback Triggers
An automatic rollback to the previous traffic tier (or 0% if critical) is triggered immediately when:
1. Parity falls below threshold limits for 3 consecutive execution windows.
2. A single duplicate execution or lease leak is detected.
3. Sustained 429 rate limit triggers indicate quota manager failures.
4. A deterministic replay mismatch occurs.

---

## 4. Required Evidence Checklist

Before Phase 2 is signed off, the following evidence documents must be generated and stored under `reports/`:

- [ ] **Provider Qualification Reports** (`reports/providers/gemini.md` & `reports/providers/openrouter.md`)
- [ ] **Benchmark Qualification Report** (`reports/benchmark_report.md`)
- [ ] **Deterministic Replay Log & Report** (`reports/replay_report.md`)
- [ ] **Shadow Execution Parity Report** (`reports/shadow_report.md`)
- [ ] **Final Production Qualification Summary** (`reports/production_qualification.md`)
