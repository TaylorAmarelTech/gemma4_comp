"""Per-tenant token-bucket rate limiter.

In-process token-bucket implementation suitable for single-replica or
sticky-session deployments. For multi-replica stateful rate-limiting
across pods, swap the in-memory store for Redis — the public API
([`RateLimitMiddleware`][duecare.server.ratelimit.RateLimitMiddleware]
+ [`record_request`][duecare.server.ratelimit.record_request]) is
unchanged.

Two limits enforced per tenant:

  - ``DUECARE_RATE_LIMIT_PER_MIN``  (default 60) — request-per-minute
  - ``DUECARE_CONCURRENCY_PER_TENANT`` (default 10) — in-flight cap

When either is exceeded, the request returns HTTP 429 with a
``Retry-After`` header. The 429 increment lands on
``duecare_rate_limit_rejections_total{tenant, reason}``.

Per-route exemption: any path in ``EXEMPT_PATHS`` bypasses both
limits. By default that's healthchecks + the metrics endpoint.
"""
from __future__ import annotations

import asyncio
import os
import time
from collections import defaultdict
from typing import Any, Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from duecare.server import observability as obs


EXEMPT_PATHS: tuple[str, ...] = (
    "/healthz", "/health", "/metrics", "/", "/static",
    "/openapi.json", "/docs", "/redoc",
)


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


class _TokenBucket:
    """Classic token bucket. Refills at ``rate_per_sec`` per second
    up to ``capacity``. Thread-safe under asyncio (single-threaded
    event loop)."""

    __slots__ = ("capacity", "rate_per_sec", "_tokens", "_last")

    def __init__(self, capacity: int, rate_per_sec: float) -> None:
        self.capacity = capacity
        self.rate_per_sec = rate_per_sec
        self._tokens = float(capacity)
        self._last = time.monotonic()

    def take(self, n: float = 1.0) -> bool:
        now = time.monotonic()
        elapsed = now - self._last
        self._last = now
        self._tokens = min(
            self.capacity,
            self._tokens + elapsed * self.rate_per_sec,
        )
        if self._tokens >= n:
            self._tokens -= n
            return True
        return False

    def retry_after_seconds(self, n: float = 1.0) -> float:
        if self._tokens >= n:
            return 0.0
        deficit = n - self._tokens
        return max(0.5, deficit / self.rate_per_sec)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """In-process per-tenant rate limiter."""

    def __init__(
        self,
        app: Any,
        rpm: int | None = None,
        concurrency: int | None = None,
    ) -> None:
        super().__init__(app)
        self._rpm = rpm or _env_int("DUECARE_RATE_LIMIT_PER_MIN", 60)
        self._concurrency = concurrency or _env_int(
            "DUECARE_CONCURRENCY_PER_TENANT", 10,
        )
        self._buckets: dict[str, _TokenBucket] = defaultdict(
            lambda: _TokenBucket(
                capacity=self._rpm,
                rate_per_sec=self._rpm / 60.0,
            )
        )
        self._in_flight: dict[str, int] = defaultdict(int)
        self._lock = asyncio.Lock()

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        # Skip exempt paths
        if any(request.url.path.startswith(p) for p in EXEMPT_PATHS):
            return await call_next(request)

        tenant = getattr(request.state, "tenant_id", "public")

        # Check rate-per-minute
        bucket = self._buckets[tenant]
        if not bucket.take(1.0):
            obs.rate_limit_rejections_total.labels(
                tenant=tenant, reason="rpm",
            ).inc()
            retry = int(bucket.retry_after_seconds(1.0))
            return JSONResponse(
                status_code=429,
                headers={"Retry-After": str(max(1, retry))},
                content={
                    "error": "rate_limit_exceeded",
                    "scope": "requests_per_minute",
                    "tenant": tenant,
                    "limit": self._rpm,
                    "retry_after_seconds": retry,
                },
            )

        # Check concurrency cap
        async with self._lock:
            if self._in_flight[tenant] >= self._concurrency:
                obs.rate_limit_rejections_total.labels(
                    tenant=tenant, reason="concurrency",
                ).inc()
                return JSONResponse(
                    status_code=429,
                    headers={"Retry-After": "5"},
                    content={
                        "error": "rate_limit_exceeded",
                        "scope": "concurrency",
                        "tenant": tenant,
                        "limit": self._concurrency,
                        "retry_after_seconds": 5,
                    },
                )
            self._in_flight[tenant] += 1
            obs.tenant_concurrency_in_flight.labels(
                tenant=tenant,
            ).set(self._in_flight[tenant])

        try:
            return await call_next(request)
        finally:
            async with self._lock:
                self._in_flight[tenant] -= 1
                obs.tenant_concurrency_in_flight.labels(
                    tenant=tenant,
                ).set(self._in_flight[tenant])
