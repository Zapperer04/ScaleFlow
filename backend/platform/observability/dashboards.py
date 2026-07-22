import json

GRAFANA_DASHBOARD_JSON = {
  "annotations": {
    "list": []
  },
  "editable": True,
  "fiscalYearStartMonth": 0,
  "graphTooltip": 0,
  "id": 1,
  "links": [],
  "liveNow": False,
  "panels": [
    {
      "collapsed": False,
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 0,
        "y": 0
      },
      "id": 1,
      "title": "Requests per Second",
      "type": "timeseries",
      "targets": [
        {
          "expr": "rate(mrrag_requests_total[1m])",
          "legendFormat": "{{path}}",
          "refId": "A"
        }
      ]
    },
    {
      "collapsed": False,
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 12,
        "y": 0
      },
      "id": 2,
      "title": "System Latency Averages",
      "type": "timeseries",
      "targets": [
        {
          "expr": "mrrag_latency_seconds_avg",
          "legendFormat": "{{metric}}",
          "refId": "A"
        }
      ]
    },
    {
      "collapsed": False,
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 0,
        "y": 8
      },
      "id": 3,
      "title": "Daily API Cost",
      "type": "timeseries",
      "targets": [
        {
          "expr": "increase(mrrag_cost_usd_total[24h])",
          "refId": "A"
        }
      ]
    },
    {
      "collapsed": False,
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 12,
        "y": 8
      },
      "id": 4,
      "title": "Queue Depth",
      "type": "timeseries",
      "targets": [
        {
          "expr": "mrrag_queue_depth",
          "refId": "A"
        }
      ]
    }
  ],
  "schemaVersion": 36,
  "style": "dark",
  "tags": ["mrrag", "serving"],
  "time": {
    "from": "now-1h",
    "to": "now"
  },
  "title": "MR-RAG Serving Platform Monitor",
  "version": 1
}

def get_dashboard_json() -> str:
    return json.dumps(GRAFANA_DASHBOARD_JSON, indent=2)
