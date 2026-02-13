"""
Request ID and structured logging middleware.

Generates an 8-char UUID per request, logs method/path/status/duration,
and returns X-Request-ID header in the response.
"""

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("app.request")

# Paths to skip verbose logging for
_QUIET_PREFIXES = ("/api/health", "/static")


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = uuid.uuid4().hex[:8]
        request.state.request_id = request_id

        path = request.url.path
        quiet = any(path.startswith(prefix) for prefix in _QUIET_PREFIXES)

        start = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start) * 1000

        response.headers["X-Request-ID"] = request_id

        # Record stats (tracker may not be ready during startup)
        try:
            from app.main import get_stats_tracker
            stats = get_stats_tracker()
            stats.record_request(path)
            if response.status_code >= 400:
                stats.record_error(path)
        except RuntimeError:
            pass

        if not quiet:
            ip = _get_client_ip(request)
            logger.info(
                f"[{request_id}] {request.method} {path} -> "
                f"{response.status_code} ({duration_ms:.0f}ms) IP={ip}"
            )

        return response
