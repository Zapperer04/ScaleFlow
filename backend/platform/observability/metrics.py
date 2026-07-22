import time
from typing import Dict, Any

class MetricsCollector:
    def __init__(self):
        self.request_counts = {"/chat": 0, "/upload": 0, "/retrieve": 0}
        self.errors_count = 0
        self.rate_limits_429 = 0
        
        # Latencies
        self.latencies = {
            "retrieval": [],
            "generation": [],
            "reranker": [],
            "planner": [],
            "verification": [],
            "provider": [],
            "total": []
        }
        
        # Token usage & Cost
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_cost = 0.0
        
        # Cache
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Confidence
        self.retrieval_confidence = []
        self.answer_confidence = []

    def record_request(self, path: str):
        if path in self.request_counts:
            self.request_counts[path] += 1

    def record_error(self):
        self.errors_count += 1

    def record_429(self):
        self.rate_limits_429 += 1

    def record_latency(self, metric: str, duration: float):
        if metric in self.latencies:
            self.latencies[metric].append(duration)
            # Cap history to prevent memory leak
            if len(self.latencies[metric]) > 1000:
                self.latencies[metric].pop(0)

    def record_tokens(self, prompt: int, completion: int, cost: float = 0.0):
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        self.total_cost += cost

    def record_cache(self, hit: bool):
        if hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1

    def record_confidence(self, retrieval: float, answer: float):
        self.retrieval_confidence.append(retrieval)
        self.answer_confidence.append(answer)
        if len(self.retrieval_confidence) > 1000:
            self.retrieval_confidence.pop(0)
            self.answer_confidence.pop(0)

    def generate_prometheus_metrics(self) -> str:
        lines = []
        
        # Requests
        for path, count in self.request_counts.items():
            lines.append(f'mrrag_requests_total{{path="{path}"}} {count}')
            
        # Errors & 429
        lines.append(f'mrrag_errors_total {self.errors_count}')
        lines.append(f'mrrag_rate_limits_total {self.rate_limits_429}')
        
        # Latency averages
        for metric, values in self.latencies.items():
            avg = sum(values) / len(values) if values else 0.0
            lines.append(f'mrrag_latency_seconds_avg{{metric="{metric}"}} {avg:.4f}')
            
        # Tokens and Costs
        lines.append(f'mrrag_prompt_tokens_total {self.prompt_tokens}')
        lines.append(f'mrrag_completion_tokens_total {self.completion_tokens}')
        lines.append(f'mrrag_cost_usd_total {self.total_cost:.6f}')
        
        # Cache hits
        total_cache = self.cache_hits + self.cache_misses
        ratio = self.cache_hits / total_cache if total_cache > 0 else 0.0
        lines.append(f'mrrag_cache_hits_total {self.cache_hits}')
        lines.append(f'mrrag_cache_misses_total {self.cache_misses}')
        lines.append(f'mrrag_cache_hit_ratio {ratio:.4f}')
        
        # Confidence
        avg_ret_conf = sum(self.retrieval_confidence) / len(self.retrieval_confidence) if self.retrieval_confidence else 0.0
        avg_ans_conf = sum(self.answer_confidence) / len(self.answer_confidence) if self.answer_confidence else 0.0
        lines.append(f'mrrag_retrieval_confidence_avg {avg_ret_conf:.4f}')
        lines.append(f'mrrag_answer_confidence_avg {avg_ans_conf:.4f}')
        
        # Queue depth (from DB)
        from backend.platform.runtime.app_state import app_state
        queue_depth = 0
        if app_state.db_conn:
            try:
                cursor = app_state.db_conn.cursor()
                cursor.execute("SELECT COUNT(*) as count FROM job_queue WHERE status = 'queued'")
                queue_depth = cursor.fetchone()["count"]
            except Exception:
                pass
        lines.append(f'mrrag_queue_depth {queue_depth}')
        
        return "\n".join(lines) + "\n"
