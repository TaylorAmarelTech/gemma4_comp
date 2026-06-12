"""Per-IP rate limiting for the hub's public mutation endpoints.

The hub's POST endpoints (newsletter subscribe, outreach observe/campaign,
signal intake, opencrawl updates) are unauthenticated BY DESIGN — anyone in
civil society can contribute — so honest throttling is the abuse control:
without it, one client can pump the outreach priority ranking or flood the
subscriber store at line rate.

Fixed-window counters keyed by ``(client_ip, path_group)``, in-memory and
per-process (Render runs a single instance; a multi-instance deployment
would move this to a shared store). Uses only starlette (already a FastAPI
dependency) — no new packages.

Configure via ``DUECARE_RATE_LIMIT="requests/window_seconds"``;
``"0"`` disables (used by load tests). Default: 30 requests / 300 s.
"""
from __future__ import annotations

import os
import time
from collections import deque
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

DEFAULT_LIMIT = 30
DEFAULT_WINDOW_SECONDS = 300
MAX_TRACKED_KEYS = 10_000  # hard memory bound for a long-lived public process

# Path prefixes that mutate hub state and face the public internet.
LIMITED_PREFIXES: tuple[str, ...] = (
    "/api/newsletter/subscribe",
    "/api/outreach/observe",
    "/api/outreach/campaign",
    "/api/hub/signals",
    "/api/hub/opencrawl",
)


def parse_rate_limit_env(raw: str) -> tuple[int, int]:
    """Parse ``"requests/window_seconds"``. ``"0"`` disables; junk falls
    back to the defaults (fail-safe: misconfiguration must not open the
    endpoints wide)."""
    raw = (raw or "").strip()
    if not raw:
        return DEFAULT_LIMIT, DEFAULT_WINDOW_SECONDS
    if raw == "0":
        return 0, 0
    try:
        requests_part, _, window_part = raw.partition("/")
        limit = max(1, int(requests_part))
        window = max(1, int(window_part)) if window_part else DEFAULT_WINDOW_SECONDS
        return limit, window
    except ValueError:
        return DEFAULT_LIMIT, DEFAULT_WINDOW_SECONDS


def client_ip(request: Request) -> str:
    """First X-Forwarded-For hop (Render terminates TLS in front of us),
    else the direct peer address."""
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip() or "unknown"
    return request.client.host if request.client else "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """429s POSTs to LIMITED_PREFIXES past ``limit`` per ``window``."""

    def __init__(self, app, *, limit: Optional[int] = None,
                 window_seconds: Optional[int] = None) -> None:
        super().__init__(app)
        env_limit, env_window = parse_rate_limit_env(
            os.environ.get("DUECARE_RATE_LIMIT", ""))
        self.limit = env_limit if limit is None else limit
        self.window = env_window if window_seconds is None else window_seconds
        self._hits: dict[str, deque] = {}

    def check(self, key: str, now: float) -> Optional[int]:
        """Record one hit for ``key`` at ``now``.

        Returns None when allowed, or the Retry-After seconds when over
        the limit. Separated from dispatch so the window arithmetic is
        unit-testable with synthetic clocks.
        """
        bucket = self._hits.get(key)
        if bucket is None:
            if len(self._hits) >= MAX_TRACKED_KEYS:
                # Blunt but bounded: dropping all counters briefly relaxes
                # limits instead of growing memory without bound.
                self._hits.clear()
            bucket = self._hits[key] = deque()
        cutoff = now - self.window
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= self.limit:
            return max(1, int(bucket[0] + self.window - now))
        bucket.append(now)
        return None

    async def dispatch(self, request: Request, call_next) -> Response:
        if self.limit <= 0 or request.method != "POST":
            return await call_next(request)
        path = request.url.path
        prefix = next((p for p in LIMITED_PREFIXES if path.startswith(p)), None)
        if prefix is None:
            return await call_next(request)
        retry_after = self.check(f"{client_ip(request)}|{prefix}", time.monotonic())
        if retry_after is not None:
            return JSONResponse(
                {
                    "ok": False,
                    "error": "rate_limited",
                    "detail": (
                        f"limit {self.limit} requests per {self.window}s "
                        f"per client for {prefix}"
                    ),
                    "retry_after_seconds": retry_after,
                },
                status_code=429,
                headers={"Retry-After": str(retry_after)},
            )
        return await call_next(request)


__all__ = [
    "DEFAULT_LIMIT",
    "DEFAULT_WINDOW_SECONDS",
    "LIMITED_PREFIXES",
    "RateLimitMiddleware",
    "client_ip",
    "parse_rate_limit_env",
]
