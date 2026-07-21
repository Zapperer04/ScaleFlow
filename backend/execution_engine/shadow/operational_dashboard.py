"""
OperationalDashboard — Task 7 of Phase 2C
Generates runtime JSON/MD dashboard files from live runtime data only.
Called periodically during long-running shadow tests and after benchmarks.

Outputs:
  reports/provider_health.json
  reports/provider_cooldowns.json
  reports/provider_circuit_breakers.json
  reports/shadow_statistics.json
  reports/routing_history.json
"""
import os
import json
import time
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("OperationalDashboard")


class OperationalDashboard:

    REPORTS_DIR = "reports"

    def __init__(
        self,
        health_service=None,
        broker=None,
        shadow_stats: Optional[Dict] = None,
    ):
        self.health_service = health_service
        self.broker = broker
        self.shadow_stats = shadow_stats or {}
        os.makedirs(self.REPORTS_DIR, exist_ok=True)

    # ------------------------------------------------------------------
    # Individual dashboard writers
    # ------------------------------------------------------------------

    def write_provider_health(self) -> dict:
        from execution_engine.control_plane.adaptive_rate_manager import get_adaptive_rate_manager
        from execution_engine.control_plane.circuit_breaker import get_circuit_registry

        providers = set()
        arm = get_adaptive_rate_manager()
        cr = get_circuit_registry()
        providers.update(arm.all_provider_ids())
        providers.update(cr.all_provider_ids())

        if self.health_service:
            # Add health_service providers if known
            pass

        data = {}
        for pid in providers or ["gemini", "openrouter"]:
            health_score = 100.0
            detailed = {}
            if self.health_service:
                try:
                    health_score = self.health_service.get_health_score(pid)
                    detailed = self.health_service.get_detailed_health(pid)
                except Exception:
                    pass

            rate_state = arm.get_state(pid).to_dict()
            cb_state = cr.get(pid).to_dict()

            data[pid] = {
                "provider_id": pid,
                "health_score": round(health_score, 2),
                "health_detail": detailed,
                "rate_state": rate_state,
                "circuit_breaker": {
                    "state": cb_state["state"],
                    "open_count": cb_state["open_count"],
                    "recovery_count": cb_state["recovery_count"],
                },
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }

        path = os.path.join(self.REPORTS_DIR, "provider_health.json")
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"[Dashboard] Wrote {path}")
        return data

    def write_provider_cooldowns(self) -> dict:
        from execution_engine.control_plane.circuit_breaker import get_cooldown_scheduler

        sched = get_cooldown_scheduler()
        data = {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "cooldowns": sched.all_cooldowns(),
            "recent_cooldown_events": sched.recent_events(50),
        }

        path = os.path.join(self.REPORTS_DIR, "provider_cooldowns.json")
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"[Dashboard] Wrote {path}")
        return data

    def write_circuit_breakers(self) -> dict:
        from execution_engine.control_plane.circuit_breaker import get_circuit_registry

        cr = get_circuit_registry()
        data = {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "circuit_breakers": cr.all_states(),
        }

        path = os.path.join(self.REPORTS_DIR, "provider_circuit_breakers.json")
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"[Dashboard] Wrote {path}")
        return data

    def write_shadow_statistics(self, stats: Optional[Dict] = None) -> dict:
        stats = stats or self.shadow_stats
        data = {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "statistics": stats,
        }

        path = os.path.join(self.REPORTS_DIR, "shadow_statistics.json")
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"[Dashboard] Wrote {path}")
        return data

    def write_routing_history(self) -> dict:
        history = []
        if self.broker and hasattr(self.broker, "get_routing_history"):
            history = self.broker.get_routing_history()

        data = {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_decisions": len(history),
            "routing_decisions": history[-200:],  # Keep last 200
        }

        path = os.path.join(self.REPORTS_DIR, "routing_history.json")
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"[Dashboard] Wrote {path}")
        return data

    def write_all(self, stats: Optional[Dict] = None) -> Dict[str, Any]:
        """Write all dashboard files and return combined summary."""
        health = self.write_provider_health()
        cooldowns = self.write_provider_cooldowns()
        cbs = self.write_circuit_breakers()
        shadow = self.write_shadow_statistics(stats)
        routing = self.write_routing_history()

        return {
            "provider_health": health,
            "cooldowns": cooldowns,
            "circuit_breakers": cbs,
            "shadow_statistics": shadow,
            "routing_history": routing,
        }

    # ------------------------------------------------------------------
    # Markdown report generators — Task 7
    # ------------------------------------------------------------------

    def write_provider_health_report(
        self, provider_history: List[dict], run_start: float, run_end: float
    ):
        os.makedirs(self.REPORTS_DIR, exist_ok=True)
        providers = list(set(r.get("provider") for r in provider_history if r.get("provider")))

        lines = [
            "# Provider Health Report\n",
            f"Generated: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\n",
            f"Runtime: {(run_end - run_start) / 60.0:.1f} minutes\n",
            "---",
            "| Provider | Requests | Success | Failures | 429s | Timeouts | "
            "Avg Latency | Avg Cost | Health Score |",
            "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
        ]

        for prov in sorted(providers):
            runs = [r for r in provider_history if r.get("provider") == prov]
            total = len(runs)
            successes = sum(1 for r in runs if r.get("success"))
            failures = total - successes
            rate_429 = sum(1 for r in runs if r.get("is_quota_event") or "429" in str(r.get("error", "")).lower())
            timeouts = sum(1 for r in runs if r.get("is_timeout") or "timeout" in str(r.get("error", "")).lower())
            avg_lat = sum(r.get("latency_sec", 0) for r in runs) / max(1, total)
            avg_cost = sum(r.get("cost", 0) for r in runs) / max(1, total)

            health = "N/A"
            if self.health_service:
                try:
                    health = f"{self.health_service.get_health_score(prov):.1f}"
                except Exception:
                    pass

            lines.append(
                f"| {prov} | {total} | {successes} | {failures} | {rate_429} | "
                f"{timeouts} | {avg_lat:.2f}s | ${avg_cost:.6f} | {health} |"
            )

        path = os.path.join(self.REPORTS_DIR, "provider_health_report.md")
        with open(path, "w") as f:
            f.write("\n".join(lines) + "\n")
        print(f"Generated {path}")

    def write_provider_resilience_report(self, provider_history: List[dict]):
        from execution_engine.control_plane.circuit_breaker import get_circuit_registry, get_cooldown_scheduler

        cr = get_circuit_registry()
        cs = get_cooldown_scheduler()
        lines = [
            "# Provider Resilience Report\n",
            f"Generated: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\n",
            "---",
        ]

        for pid in ["gemini", "openrouter"]:
            cb = cr.get(pid).to_dict()
            cooldowns_info = cs.all_cooldowns().get(pid, {})
            lines += [
                f"\n## {pid.upper()}",
                f"- Circuit Breaker State: `{cb['state']}`",
                f"- Open Count: {cb['open_count']}",
                f"- Recovery Count: {cb['recovery_count']}",
                f"- Consecutive Failures: {cb['consecutive_failures']}",
                f"- Last Failure Reason: {cb['last_failure_reason'] or 'None'}",
                f"- Cooldown Events: {cooldowns_info.get('event_count', 0)}",
                f"- Recent CB Transitions:",
            ]
            for tr in cb.get("recent_transitions", []):
                lines.append(
                    f"  - {tr['iso_time']}: {tr['from_state']} → {tr['to_state']} ({tr['reason']})"
                )

        path = os.path.join(self.REPORTS_DIR, "provider_resilience_report.md")
        with open(path, "w") as f:
            f.write("\n".join(lines) + "\n")
        print(f"Generated {path}")

    def write_cooldown_statistics(self, provider_history: List[dict]):
        from execution_engine.control_plane.circuit_breaker import get_cooldown_scheduler
        cs = get_cooldown_scheduler()
        events = cs.recent_events(100)
        cooldowns = cs.all_cooldowns()

        lines = [
            "# Cooldown Statistics Report\n",
            f"Generated: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\n",
            f"Total Cooldown Events: {len(events)}\n",
            "---",
            "| Provider | Events | Last Cooldown Duration | In Cooldown Now |",
            "| :--- | :---: | :---: | :---: |",
        ]
        for pid, info in cooldowns.items():
            provevents = [e for e in events if e.get("provider") == pid]
            last_dur = provevents[-1]["cooldown_sec"] if provevents else 0
            lines.append(
                f"| {pid} | {len(provevents)} | {last_dur:.1f}s | {info['in_cooldown']} |"
            )

        lines += ["", "## Recent Cooldown Events", "| Time | Provider | Duration | Retry-After Hint |",
                  "| :--- | :--- | :--- | :--- |"]
        for ev in events[-20:]:
            lines.append(
                f"| {ev.get('cooldown_until', 'N/A')} | {ev['provider']} | "
                f"{ev['cooldown_sec']:.1f}s | {ev.get('retry_after_hint', 0):.0f}s |"
            )

        path = os.path.join(self.REPORTS_DIR, "cooldown_statistics.md")
        with open(path, "w") as f:
            f.write("\n".join(lines) + "\n")
        print(f"Generated {path}")

    def write_broker_adaptation_report(self, provider_history: List[dict]):
        routing_history = []
        if self.broker and hasattr(self.broker, "get_routing_history"):
            routing_history = self.broker.get_routing_history()

        total_decisions = len(routing_history)
        successful_routes = sum(1 for d in routing_history if d.get("selected_provider"))
        total_rejections = sum(len(d.get("providers_rejected", {})) for d in routing_history)

        lines = [
            "# Broker Adaptation Report\n",
            f"Generated: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\n",
            f"- Total Routing Decisions: {total_decisions}",
            f"- Successful Routes: {successful_routes}",
            f"- Total Provider Rejections: {total_rejections}",
            "\n## Rejection Reason Summary",
        ]

        all_rejections: Dict[str, int] = {}
        for d in routing_history:
            for pid, reason in d.get("providers_rejected", {}).items():
                category = reason.split(":")[0] if ":" in reason else reason
                all_rejections[category] = all_rejections.get(category, 0) + 1

        lines += ["| Rejection Category | Count |", "| :--- | :---: |"]
        for cat, count in sorted(all_rejections.items(), key=lambda x: -x[1]):
            lines.append(f"| {cat} | {count} |")

        lines += [
            "\n## Recent Routing Decisions (last 20)",
            "| Time | Selected | Rejected |",
            "| :--- | :--- | :--- |",
        ]
        for d in routing_history[-20:]:
            iso_time = d.get("iso_time", "N/A")
            selected = d.get("selected_provider", "NONE")
            rejected_str = ", ".join(
                f"{p}({r[:30]})" for p, r in d.get("providers_rejected", {}).items()
            )
            lines.append(f"| {iso_time} | {selected} | {rejected_str} |")

        path = os.path.join(self.REPORTS_DIR, "broker_adaptation_report.md")
        with open(path, "w") as f:
            f.write("\n".join(lines) + "\n")
        print(f"Generated {path}")

    def write_shadow_runtime_report(self, stats: dict, run_start: float, run_end: float):
        duration_min = (run_end - run_start) / 60.0
        lines = [
            "# Shadow Runtime Report\n",
            f"Generated: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}",
            f"Duration: {duration_min:.1f} minutes\n",
            "## Runtime Statistics",
        ]

        for k, v in stats.items():
            lines.append(f"- **{k.replace('_', ' ').title()}**: {v}")

        path = os.path.join(self.REPORTS_DIR, "shadow_runtime_report.md")
        with open(path, "w") as f:
            f.write("\n".join(lines) + "\n")
        print(f"Generated {path}")

    def write_qualification_report(
        self, stats: dict, provider_history: List[dict], decision: str, run_start: float, run_end: float
    ):
        duration_min = (run_end - run_start) / 60.0
        total_calls = stats.get("total_provider_calls", 0)
        successful = stats.get("successful_calls", 0)
        retries = stats.get("total_retries", 0)
        rate_429 = stats.get("total_429s", 0)
        timeouts = stats.get("total_timeouts", 0)
        cb_opens = stats.get("cb_open_events", 0)
        cb_recoveries = stats.get("cb_recovery_events", 0)
        cooldown_events = stats.get("total_cooldown_events", 0)
        avg_broker_latency = stats.get("avg_broker_latency_ms", 0)
        avg_provider_latency = stats.get("avg_provider_latency_sec", 0)
        avg_cost = stats.get("avg_cost", 0)
        avg_tokens = stats.get("avg_tokens", 0)
        documents = stats.get("documents", 0)
        pages = stats.get("pages", documents)

        lines = [
            "# Qualification Report\n",
            f"Generated: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}",
            f"Qualification Duration: {duration_min:.1f} minutes\n",
            f"## Final Decision: `{decision}`\n",
            "## Required Runtime Evidence",
            f"| Metric | Value |",
            f"| :--- | :---: |",
            f"| Documents | {documents} |",
            f"| Pages | {pages} |",
            f"| Provider Calls | {total_calls} |",
            f"| Retries | {retries} |",
            f"| 429s (Quota Events) | {rate_429} |",
            f"| Timeouts | {timeouts} |",
            f"| Cooldown Events | {cooldown_events} |",
            f"| Circuit Breaker Opens | {cb_opens} |",
            f"| Circuit Breaker Recoveries | {cb_recoveries} |",
            f"| Avg Broker Latency | {avg_broker_latency:.1f}ms |",
            f"| Avg Provider Latency | {avg_provider_latency:.3f}s |",
            f"| Avg Cost | ${avg_cost:.6f} |",
            f"| Avg Tokens | {avg_tokens:.0f} |",
            f"| Qualification Duration | {duration_min:.1f} min |",
            "\n## Provider Qualification Summary",
            "> [!NOTE]",
            "> HTTP 429 responses indicate provider quota policy was reached,",
            "> NOT that the execution engine failed. The engine is evaluated on whether",
            "> it recovers gracefully from quota exhaustion.",
        ]

        path = os.path.join(self.REPORTS_DIR, "qualification_report.md")
        with open(path, "w") as f:
            f.write("\n".join(lines) + "\n")
        print(f"Generated {path}")
