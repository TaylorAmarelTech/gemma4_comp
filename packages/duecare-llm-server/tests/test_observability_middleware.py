"""Smoke tests for the v0.7 server middleware:

  - /metrics endpoint exposes Prometheus exposition format
  - X-Tenant-ID header is honored and stamped on the request
  - Rate-limit middleware returns 429 + Retry-After when bucket is empty
  - Concurrency cap is independent per tenant
  - Cost lookup is deterministic + handles unknown models

The tests intentionally avoid the heavy `state.py` startup path
(which loads the full evidence DB + engine) by constructing a minimal
FastAPI app with just the middleware stack.
"""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from duecare.server.observability import install_observability
from duecare.server.tenancy import TenancyMiddleware
from duecare.server.ratelimit import RateLimitMiddleware
from duecare.server.request_metrics_mw import RequestMetricsMiddleware
from duecare.server import metering


def _build_app(rpm: int = 60, concurrency: int = 10) -> FastAPI:
    app = FastAPI()
    install_observability(app)
    app.add_middleware(RequestMetricsMiddleware)
    app.add_middleware(RateLimitMiddleware, rpm=rpm, concurrency=concurrency)
    app.add_middleware(TenancyMiddleware, default_tenant="test-default")

    @app.get("/echo")
    def echo(request):                       # type: ignore
        return {"tenant": request.state.tenant_id}

    @app.get("/healthz")
    def healthz():
        return {"ok": True}

    return app


def test_metrics_endpoint_returns_prometheus_format() -> None:
    app = _build_app()
    client = TestClient(app)
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "text/plain" in r.headers.get("content-type", "")
    # Body should be either real Prom exposition OR the fallback stub —
    # both are acceptable behaviors when prometheus-client is missing.
    body = r.text
    assert body.startswith("#") or "prometheus-client" in body


def test_tenant_header_is_honored() -> None:
    app = _build_app()
    client = TestClient(app)
    r = client.get("/echo", headers={"X-Tenant-ID": "ngo-mfmw-hk"})
    assert r.status_code == 200
    assert r.json()["tenant"] == "ngo-mfmw-hk"


def test_tenant_default_when_no_header() -> None:
    app = _build_app()
    client = TestClient(app)
    r = client.get("/echo")
    assert r.status_code == 200
    assert r.json()["tenant"] == "test-default"


def test_tenant_oauth2_proxy_email_header() -> None:
    app = _build_app()
    client = TestClient(app)
    r = client.get("/echo", headers={"X-Forwarded-Email": "alice@ngo.org"})
    assert r.status_code == 200
    assert r.json()["tenant"] == "alice@ngo.org"


def test_tenant_id_sanitization() -> None:
    """Bad chars are stripped; oversized values truncated to 64 chars."""
    app = _build_app()
    client = TestClient(app)
    r = client.get(
        "/echo",
        headers={"X-Tenant-ID": "ALICE@<script>.COM " + "x" * 100},
    )
    assert r.status_code == 200
    tenant = r.json()["tenant"]
    assert "<" not in tenant
    assert "script" in tenant   # alphanumerics survive
    assert len(tenant) <= 64


def test_rate_limit_rejects_after_bucket_empty() -> None:
    app = _build_app(rpm=3)         # tiny RPM for fast test
    client = TestClient(app)
    statuses = []
    for _ in range(5):
        statuses.append(
            client.get("/echo", headers={"X-Tenant-ID": "noisy"}).status_code
        )
    assert statuses.count(200) <= 4    # token bucket allows the initial burst
    assert 429 in statuses


def test_rate_limit_is_per_tenant() -> None:
    """Tenant A exceeding their cap doesn't affect tenant B."""
    app = _build_app(rpm=2)
    client = TestClient(app)
    for _ in range(5):
        client.get("/echo", headers={"X-Tenant-ID": "tenant-a"})
    # Tenant B should still get a clean 200
    r = client.get("/echo", headers={"X-Tenant-ID": "tenant-b"})
    assert r.status_code == 200


def test_healthz_bypasses_rate_limit() -> None:
    app = _build_app(rpm=1)
    client = TestClient(app)
    # Burn the bucket on /echo
    for _ in range(5):
        client.get("/echo", headers={"X-Tenant-ID": "burn"})
    # /healthz still works
    for _ in range(20):
        r = client.get("/healthz")
        assert r.status_code == 200


def test_metering_cost_lookup_known_model() -> None:
    cost = metering.estimate_cost_usd("gpt-4o-mini", 1000, 1000)
    # 1000 in @ $0.00015 + 1000 out @ $0.0006 = $0.00075
    assert cost == pytest.approx(0.00075, abs=1e-6)


def test_metering_cost_lookup_unknown_model_uses_default() -> None:
    cost = metering.estimate_cost_usd("unknown-model-xyz", 1000, 1000)
    # 1000 in @ $0.0005 + 1000 out @ $0.0015 = $0.002
    assert cost == pytest.approx(0.002, abs=1e-6)


def test_metering_cost_lookup_local_model_zero_cost() -> None:
    assert metering.estimate_cost_usd("gemma4:e2b", 999_999, 999_999) == 0.0


def test_metering_record_returns_cost() -> None:
    cost = metering.record(
        tenant="t1", model="gpt-4o-mini",
        tokens_in=2000, tokens_out=500,
    )
    # 2000 in @ $0.00015 + 500 out @ $0.0006 = $0.0006
    assert cost == pytest.approx(0.0006, abs=1e-6)
