"""Per-request metrics middleware — counters + duration histogram.

Stamps the standard `duecare_chat_requests_total` and
`duecare_chat_request_duration_seconds` series after every request,
labelled by tenant + route + status. Sits between the tenancy
middleware (which sets ``request.state.tenant_id``) and the route
handler.

The "model" + "harness_layer" labels on the histogram are populated
generically here as ``"unknown"`` / ``"http"``. Route handlers that
want finer attribution should observe the histogram themselves with
the right label set after their model call returns; this middleware
provides the always-on baseline so nothing goes unmeasured.
"""
from __future__ import annotations

import time
from typing import Any, Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from duecare.server import observability as obs


# Routes whose duration we don't want to plot (probes / static files
# would dominate the histogram with sub-ms responses).
_NO_HISTOGRAM_PATHS = ("/healthz", "/health", "/metrics", "/static")


class RequestMetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        tenant = getattr(request.state, "tenant_id", "public")
        route = request.url.path
        start = time.perf_counter()
        try:
            response = await call_next(request)
            status = str(response.status_code)
        except Exception:
            obs.chat_requests_total.labels(
                tenant=tenant, route=route, status="500",
            ).inc()
            raise
        elapsed = time.perf_counter() - start

        obs.chat_requests_total.labels(
            tenant=tenant, route=route, status=status,
        ).inc()

        if not any(route.startswith(p) for p in _NO_HISTOGRAM_PATHS):
            obs.chat_request_duration_seconds.labels(
                tenant=tenant, model="unknown", harness_layer="http",
            ).observe(elapsed)

        return response
