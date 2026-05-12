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
``duecare_rate_limit_rejections_total{tenant, reason}`` with a hashed
tenant label.

Per-route exemption: paths in ``EXEMPT_PATHS`` bypass both limits by
exact match; ``/static/*`` also bypasses by prefix match. By default,
only health checks and static assets are exempt. Metrics remain
rate-limited to slow bearer-token guessing when metrics auth is enabled.

All unauthenticated traffic shares the ``public`` tenant bucket. Named
tenant buckets are capped and evicted with least-recently-used semantics
to avoid unbounded memory growth from hostile tenant-id churn.
"""
from __future__ import annotations

import asyncio
import os
import time
from collections import OrderedDict
from typing import Any, Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from duecare.server import observability as obs
from duecare.server.tenancy import _sanitize as _sanitize_tenant_id


EXEMPT_PATHS: tuple[str, ...] = (
    "/healthz", "/health", "/static",
)
RPM_MIN = 1
RPM_MAX = 10_000
CONCURRENCY_MIN = 1
CONCURRENCY_MAX = 1_000
TENANT_CAP_MIN = 1
TENANT_CAP_MAX = 100_000
RETRY_AFTER_SECONDS = 5


def _is_exempt_path(path: str) -> bool:
    if path.startswith("/static/"):
        return True
    return path in EXEMPT_PATHS


def _clamp_int(value: int, min_value: int, max_value: int) -> int:
    return max(min_value, min(value, max_value))


def _env_int(
    name: str,
    default: int,
    min_value: int,
    max_value: int,
) -> int:
    try:
        value = int(os.environ.get(name, default))
    except ValueError:
        value = default
    return _clamp_int(value, min_value, max_value)


def _safe_tenant_id(value: object) -> str:
    """Normalize tenant IDs using the same rules as tenancy middleware."""
    return _sanitize_tenant_id(str(value or "public"))


class _TokenBucket:
    """Classic token bucket. Refills at ``rate_per_sec`` per second
    up to ``capacity``. Callers must serialize access."""

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
        return max(1.0, deficit / self.rate_per_sec)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """In-process per-tenant rate limiter."""

    def __init__(
        self,
        app: Any,
        rpm: int | None = None,
        concurrency: int | None = None,
    ) -> None:
        super().__init__(app)
        self._rpm = (
            _clamp_int(rpm, RPM_MIN, RPM_MAX)
            if rpm is not None
            else _env_int(
                "DUECARE_RATE_LIMIT_PER_MIN", 60, RPM_MIN, RPM_MAX,
            )
        )
        self._concurrency = (
            _clamp_int(concurrency, CONCURRENCY_MIN, CONCURRENCY_MAX)
            if concurrency is not None
            else _env_int(
                "DUECARE_CONCURRENCY_PER_TENANT",
                10,
                CONCURRENCY_MIN,
                CONCURRENCY_MAX,
            )
        )
        self._max_tenants = _env_int(
            "DUECARE_RATE_LIMIT_MAX_TENANTS",
            10_000,
            TENANT_CAP_MIN,
            TENANT_CAP_MAX,
        )
        self._buckets: OrderedDict[str, _TokenBucket] = OrderedDict()
        self._in_flight: dict[str, int] = {}
        self._lock = asyncio.Lock()

    def _new_bucket(self) -> _TokenBucket:
        return _TokenBucket(
            capacity=self._rpm,
            rate_per_sec=self._rpm / 60.0,
        )

    def _get_bucket(self, tenant: str) -> _TokenBucket | None:
        bucket = self._buckets.get(tenant)
        if bucket is not None:
            self._buckets.move_to_end(tenant)
            return bucket

        if not self._evict_idle_tenant():
            return None
        bucket = self._new_bucket()
        self._buckets[tenant] = bucket
        return bucket

    def _evict_idle_tenant(self) -> bool:
        if len(self._buckets) < self._max_tenants:
            return True
        for candidate in tuple(self._buckets):
            if self._in_flight.get(candidate, 0) <= 0:
                self._buckets.pop(candidate, None)
                self._in_flight.pop(candidate, None)
                return True
        return False

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        # Skip exempt paths
        if _is_exempt_path(request.url.path):
            return await call_next(request)

        tenant = _safe_tenant_id(getattr(request.state, "tenant_id", "public"))
        tenant_label = obs.tenant_metric_label(tenant)

        # Check tenant capacity, concurrency, and RPM as one critical section.
        async with self._lock:
            bucket = self._get_bucket(tenant)
            if bucket is None:
                obs.rate_limit_rejections_total.labels(
                    tenant=tenant_label, reason="tenant_cap",
                ).inc()
                return JSONResponse(
                    status_code=429,
                    headers={"Retry-After": str(RETRY_AFTER_SECONDS)},
                    content={
                        "error": "rate_limit_exceeded",
                        "retry_after_seconds": RETRY_AFTER_SECONDS,
                    },
                )

            in_flight = self._in_flight.get(tenant, 0)
            if in_flight >= self._concurrency:
                obs.rate_limit_rejections_total.labels(
                    tenant=tenant_label, reason="concurrency",
                ).inc()
                return JSONResponse(
                    status_code=429,
                    headers={"Retry-After": str(RETRY_AFTER_SECONDS)},
                    content={
                        "error": "rate_limit_exceeded",
                        "retry_after_seconds": RETRY_AFTER_SECONDS,
                    },
                )
            if not bucket.take(1.0):
                obs.rate_limit_rejections_total.labels(
                    tenant=tenant_label, reason="rpm",
                ).inc()
                retry = max(1, int(bucket.retry_after_seconds(1.0)))
                return JSONResponse(
                    status_code=429,
                    headers={"Retry-After": str(retry)},
                    content={
                        "error": "rate_limit_exceeded",
                        "retry_after_seconds": retry,
                    },
                )

            self._in_flight[tenant] = in_flight + 1
            obs.tenant_concurrency_in_flight.labels(
                tenant=tenant_label,
            ).set(self._in_flight[tenant])

        try:
            return await call_next(request)
        finally:
            async with self._lock:
                self._in_flight[tenant] = max(
                    0,
                    self._in_flight.get(tenant, 0) - 1,
                )
                obs.tenant_concurrency_in_flight.labels(
                    tenant=tenant_label,
                ).set(self._in_flight[tenant])
