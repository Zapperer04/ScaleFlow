from flask import Flask, request, Response, jsonify
import yaml
import time
import random
import json
import os

app = Flask(__name__)
CONFIG_PATH = os.environ.get("MOCK_PROVIDER_CONFIG", "gemini.yaml")
PROVIDER_ID = os.environ.get("PROVIDER_ID", "gemini")

# Metrics
metrics = {
    "latency_sum": 0.0,
    "requests_total": 0,
    "errors_429": 0,
    "timeouts": 0,
    "malformed": 0,
    "throughput_tokens": 0
}

def load_config():
    if not os.path.exists(CONFIG_PATH):
        # Create a default configuration if it doesn't exist
        os.makedirs(os.path.dirname(CONFIG_PATH) or ".", exist_ok=True)
        default_config = {
            "provider": PROVIDER_ID,
            "stream": {
                "tokens_per_second": 50,
                "first_token_delay_ms": 500,
                "disconnect_probability": 0.0,
                "malformed_after_token": 99999,
                "timeout_probability": 0.0
            },
            "429": {
                "probability": 0.0
            },
            "latency": {
                "mean_ms": 100,
                "stddev_ms": 20
            }
        }
        with open(CONFIG_PATH, "w") as f:
            yaml.safe_dump(default_config, f)
        return default_config
    with open(CONFIG_PATH, "r") as f:
        try:
            return yaml.safe_load(f) or {}
        except Exception:
            return {}

@app.route("/metrics", methods=["GET"])
def get_metrics():
    # Expose metrics in prometheus format
    lines = [
        f'provider_requests_total{{provider="{PROVIDER_ID}"}} {metrics["requests_total"]}',
        f'provider_latency_seconds_sum{{provider="{PROVIDER_ID}"}} {metrics["latency_sum"]}',
        f'provider_429_total{{provider="{PROVIDER_ID}"}} {metrics["errors_429"]}',
        f'provider_timeout_total{{provider="{PROVIDER_ID}"}} {metrics["timeouts"]}',
        f'provider_malformed_json_total{{provider="{PROVIDER_ID}"}} {metrics["malformed"]}',
        f'provider_throughput_tokens_total{{provider="{PROVIDER_ID}"}} {metrics["throughput_tokens"]}'
    ]
    return Response("\n".join(lines), mimetype="text/plain")

@app.route("/parse", methods=["POST"])
def parse():
    metrics["requests_total"] += 1
    config = load_config()
    
    # 1. 429 probability
    p_429 = config.get("429", {}).get("probability", 0.0)
    if random.random() < p_429:
        metrics["errors_429"] += 1
        return "Too Many Requests", 429
        
    # 2. Timeout probability
    p_timeout = config.get("stream", {}).get("timeout_probability", 0.0)
    if random.random() < p_timeout:
        metrics["timeouts"] += 1
        time.sleep(10.0)  # Simulate timeout
        return "Gateway Timeout", 504

    # 3. Latency
    latency_cfg = config.get("latency", {})
    mean = latency_cfg.get("mean_ms", 100) / 1000.0
    stddev = latency_cfg.get("stddev_ms", 20) / 1000.0
    delay = max(0.0, random.normalvariate(mean, stddev))
    
    # Check if streaming is requested
    req_data = request.json or {}
    is_streaming = req_data.get("streaming", False)
    
    if is_streaming:
        stream_cfg = config.get("stream", {})
        tokens_per_sec = stream_cfg.get("tokens_per_second", 50)
        first_token_delay = stream_cfg.get("first_token_delay_ms", 500) / 1000.0
        disconnect_prob = stream_cfg.get("disconnect_probability", 0.0)
        malformed_after = stream_cfg.get("malformed_after_token", 99999)
        
        def generate():
            # First token delay
            time.sleep(first_token_delay)
            
            total_tokens = 300
            sent_tokens = 0
            
            try:
                for chunk_idx in range(10):
                    if random.random() < disconnect_prob:
                        break
                    
                    tokens_in_chunk = total_tokens // 10
                    sent_tokens += tokens_in_chunk
                    metrics["throughput_tokens"] += tokens_in_chunk
                    
                    if sent_tokens >= malformed_after:
                        metrics["malformed"] += 1
                        yield "invalid_json_stream_chunk_here{"
                        break
                    
                    time.sleep(tokens_in_chunk / tokens_per_sec)
                    chunk_data = {"nodes": [{"id": f"chunk-{chunk_idx}", "type": "text", "content": "stream content"}]}
                    yield json.dumps(chunk_data) + "\n"
            except Exception:
                pass
                
        return Response(generate(), mimetype="application/x-ndjson")
    else:
        # Non-streaming
        time.sleep(delay)
        metrics["latency_sum"] += delay
        metrics["throughput_tokens"] += 100 # standard cost
        
        stream_cfg = config.get("stream", {})
        malformed_after = stream_cfg.get("malformed_after_token", 99999)
        if malformed_after < 50:
            metrics["malformed"] += 1
            return "invalid_json_body_here{", 200
            
        result = {"nodes": [{"id": "n1", "type": "paragraph", "content": "parsed content"}]}
        return jsonify(result)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
