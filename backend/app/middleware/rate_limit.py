"""
In-memory sliding window rate limiter middleware.

Default: 20 req/min per IP on /api/chat endpoints.
Returns HTTP 429 with Retry-After header when exceeded.
"""

import time
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import settings

# Paths exempt from rate limiting
_EXEMPT_PREFIXES = ("/api/health", "/api/stats", "/static", "/test")

# {ip: [timestamp, ...]}
_request_log: dict[str, list[float]] = defaultdict(list)
_request_count = 0


def _get_client_ip(request: Request) -> str:
    """Extract client IP, respecting X-Forwarded-For for reverse proxies."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _cleanup_expired(window: float):
    """Remove entries older than the window. Called lazily every 100 requests."""
    cutoff = time.time() - window
    empty_keys = []
    for ip, timestamps in _request_log.items():
        _request_log[ip] = [t for t in timestamps if t > cutoff]
        if not _request_log[ip]:
            empty_keys.append(ip)
    for key in empty_keys:
        del _request_log[key]


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        global _request_count

        path = request.url.path

        # Skip exempt paths
        if any(path.startswith(prefix) for prefix in _EXEMPT_PREFIXES):
            return await call_next(request)

        now = time.time()
        window = 60.0  # 1 minute
        limit = settings.rate_limit_per_minute
        ip = _get_client_ip(request)

        # Lazy cleanup every 100 requests
        _request_count += 1
        if _request_count % 100 == 0:
            _cleanup_expired(window)

        # Filter to timestamps within the window
        timestamps = _request_log[ip]
        timestamps = [t for t in timestamps if t > now - window]
        _request_log[ip] = timestamps

        if len(timestamps) >= limit:
            # Calculate when the oldest request in the window expires
            retry_after = int(timestamps[0] + window - now) + 1
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Please wait.",
                    "retry_after": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

        # Record this request
        timestamps.append(now)

        return await call_next(request)
