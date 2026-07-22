PROMETHEUS_ALERT_RULES = """
groups:
  - name: mrrag_alerts
    rules:
      - alert: HighRequestFailureRate
        expr: rate(mrrag_errors_total[5m]) > 0.05
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "High API Error Rate Detected"
          description: "Errors represent >5% of request traffic over the last 5 minutes."

      - alert: EngineQueueBacklogged
        expr: mrrag_queue_depth > 50
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Indexing Queue backlog high"
          description: "More than 50 document indexing tasks are queued for longer than 5 minutes."

      - alert: ProviderRateLimitReached
        expr: rate(mrrag_rate_limits_total[1m]) > 0
        for: 0m
        labels:
          severity: warning
        annotations:
          summary: "LLM Provider Rate Limits hit (429)"
          description: "429 Rate limits were returned by the LLM gateway. Retrying and routing fallbacks."
"""

def get_alerts_yaml() -> str:
    return PROMETHEUS_ALERT_RULES
