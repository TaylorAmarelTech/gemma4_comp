"""Tenant identification middleware.

Extracts the tenant id from one of three sources, in priority order:

  1. ``X-Tenant-ID`` request header  (preferred — explicit + cheap)
  2. OIDC / JWT ``tenant`` claim     (when the upstream OAuth2 proxy
                                       has injected one as
                                       ``X-Forwarded-User`` or
                                       ``X-Auth-Request-User``)
  3. ``DUECARE_DEFAULT_TENANT`` env var  (single-tenant deployments)
  4. literal ``"public"``             (fully open / kiosk deployments)

The resolved tenant id is stashed on ``request.state.tenant_id`` for
downstream middleware (metering, ratelimit) and the route handlers.

This module deliberately does NOT do auth — that's the upstream
oauth2-proxy / Cloudflare Access / NGINX-ldap-auth's job. Tenancy is
just attribution; auth is enforcement.
"""
from __future__ import annotations

import os
from typing import Any, Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class TenancyMiddleware(BaseHTTPMiddleware):
    """Resolve tenant id and attach to request.state."""

    def __init__(
        self,
        app: Any,
        default_tenant: str | None = None,
    ) -> None:
        super().__init__(app)
        self._default = default_tenant or os.environ.get(
            "DUECARE_DEFAULT_TENANT", "public",
        )

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request.state.tenant_id = self._resolve(request)
        return await call_next(request)

    def _resolve(self, request: Request) -> str:
        # 1. Explicit header
        h = request.headers.get("x-tenant-id")
        if h and h.strip():
            return _sanitize(h)
        # 2. Upstream auth-proxy injected user/email
        for hdr in ("x-forwarded-user", "x-auth-request-user",
                     "x-forwarded-email", "x-auth-request-email"):
            v = request.headers.get(hdr)
            if v and v.strip():
                return _sanitize(v)
        # 3. Env-var default
        return self._default


def _sanitize(value: str) -> str:
    """Restrict tenant ids to a small charset so they can't break a
    Prometheus label or inject log-injection sequences. Truncate at
    64 chars."""
    safe = "".join(
        c for c in value.strip().lower()
        if c.isalnum() or c in ("-", "_", ".", "@")
    )
    return safe[:64] or "public"
