"""
Thread-safe in-memory request stats tracker.

Tracks total requests, errors, per-endpoint counts, game mode
distribution, model usage, and latency samples.
"""

import threading
import time
from collections import defaultdict


class StatsTracker:
    def __init__(self):
        self._lock = threading.Lock()
        self._start_time = time.time()
        self._total_requests = 0
        self._total_errors = 0
        self._requests_by_endpoint: dict[str, int] = defaultdict(int)
        self._errors_by_endpoint: dict[str, int] = defaultdict(int)
        self._game_modes: dict[str, int] = defaultdict(int)
        self._models: dict[str, int] = defaultdict(int)
        # Capped at 1000 samples per operation
        self._latency_samples: dict[str, list[float]] = defaultdict(list)
        self._max_samples = 1000

    def record_request(self, endpoint: str):
        with self._lock:
            self._total_requests += 1
            self._requests_by_endpoint[endpoint] += 1

    def record_error(self, endpoint: str):
        with self._lock:
            self._total_errors += 1
            self._errors_by_endpoint[endpoint] += 1

    def record_game_mode(self, mode: str):
        with self._lock:
            self._game_modes[mode] += 1

    def record_model(self, model: str):
        with self._lock:
            self._models[model] += 1

    def record_latency(self, operation: str, ms: float):
        with self._lock:
            samples = self._latency_samples[operation]
            if len(samples) >= self._max_samples:
                samples.pop(0)
            samples.append(ms)

    def get_stats(self) -> dict:
        with self._lock:
            uptime = round(time.time() - self._start_time, 1)
            error_rate = round(
                (self._total_errors / self._total_requests * 100), 2
            ) if self._total_requests > 0 else 0.0

            avg_latency = {}
            for op, samples in self._latency_samples.items():
                if samples:
                    avg_latency[op] = round(sum(samples) / len(samples), 1)

            return {
                "total_requests": self._total_requests,
                "total_errors": self._total_errors,
                "error_rate_pct": error_rate,
                "requests_by_endpoint": dict(self._requests_by_endpoint),
                "errors_by_endpoint": dict(self._errors_by_endpoint),
                "game_mode_distribution": dict(self._game_modes),
                "model_usage": dict(self._models),
                "avg_latency_ms": avg_latency,
                "stats_uptime_seconds": uptime,
            }
