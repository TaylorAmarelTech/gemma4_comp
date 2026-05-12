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
import threading
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from duecare.server.observability import install_observability, tenant_metric_label
from duecare.server.tenancy import TenancyMiddleware
from duecare.server.ratelimit import RateLimitMiddleware, _safe_tenant_id
from duecare.server.request_metrics_mw import RequestMetricsMiddleware
from duecare.server import metering


def _build_app(rpm: int = 60, concurrency: int = 10) -> FastAPI:
    app = FastAPI()
    install_observability(app)
    app.add_middleware(RequestMetricsMiddleware)
    app.add_middleware(RateLimitMiddleware, rpm=rpm, concurrency=concurrency)
    app.add_middleware(TenancyMiddleware, default_tenant="test-default")

    @app.get("/echo")
    def echo(request: Request) -> dict[str, str]:
        return {"tenant": request.state.tenant_id}

    @app.get("/healthz")
    def healthz() -> dict[str, bool]:
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


def test_metrics_endpoint_uses_configured_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DUECARE_METRICS_TOKEN", "secret-metrics-token")
    app = _build_app()
    client = TestClient(app)

    assert client.get("/metrics").status_code == 401
    response = client.get(
        "/metrics",
        headers={"Authorization": "Bearer secret-metrics-token"},
    )
    assert response.status_code == 200


def test_tenant_metric_label_hashes_raw_identifier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DUECARE_METRICS_TENANT_SALT", "stable-test-salt")
    label = tenant_metric_label("worker@example.com")

    assert label.startswith("tenant_")
    assert "worker" not in label
    assert "@" not in label
    assert label == tenant_metric_label("worker@example.com")


def test_rate_limiter_matches_tenancy_tenant_normalization() -> None:
    assert _safe_tenant_id(" Worker@Example.COM ") == "worker@example.com"


def test_metering_sanitizes_model_metric_label() -> None:
    model_label = metering._safe_model_label("evil\nmetric 1")

    assert "\n" not in model_label
    assert " " not in model_label
    assert model_label == "evilmetric1"


def test_metering_cost_override_rejects_non_json_path(tmp_path: Path) -> None:
    override = tmp_path / "costs.txt"
    override.write_text('{"model": {"in": 1, "out": 1}}', encoding="utf-8")

    assert metering._read_cost_override(str(override)) is None


def test_metrics_endpoint_does_not_expose_raw_tenant_ids() -> None:
    app = _build_app()
    client = TestClient(app)

    client.get("/echo", headers={"X-Tenant-ID": "worker@example.com"})
    response = client.get("/metrics")

    if "prometheus-client not installed" not in response.text:
        assert "worker@example.com" not in response.text
        assert tenant_metric_label("worker@example.com") in response.text


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


def test_static_subpaths_bypass_rate_limit() -> None:
    app = _build_app(rpm=1)
    client = TestClient(app)
    for _ in range(5):
        client.get("/echo", headers={"X-Tenant-ID": "burn"})
    response = client.get("/static/app.js")
    assert response.status_code != 429


def test_metrics_endpoint_is_rate_limited() -> None:
    app = _build_app(rpm=1)
    client = TestClient(app)

    statuses = [client.get("/metrics").status_code for _ in range(3)]

    assert 429 in statuses


def test_idle_tenant_buckets_are_capped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DUECARE_RATE_LIMIT_MAX_TENANTS", "2")
    app = _build_app(rpm=1)
    client = TestClient(app)

    assert client.get("/echo", headers={"X-Tenant-ID": "tenant-a"}).status_code == 200
    assert client.get("/echo", headers={"X-Tenant-ID": "tenant-a"}).status_code == 429
    assert client.get("/echo", headers={"X-Tenant-ID": "tenant-b"}).status_code == 200
    assert client.get("/echo", headers={"X-Tenant-ID": "tenant-c"}).status_code == 200

    response = client.get("/echo", headers={"X-Tenant-ID": "tenant-a"})
    assert response.status_code == 200


def test_new_tenant_rejected_when_cap_has_no_idle_slots(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DUECARE_RATE_LIMIT_MAX_TENANTS", "1")
    app = _build_app(rpm=60)
    middleware = RateLimitMiddleware(app, rpm=60)

    middleware._buckets["tenant-a"] = middleware._new_bucket()
    middleware._in_flight["tenant-a"] = 1

    assert middleware._get_bucket("tenant-b") is None


def test_rate_limiter_normalizes_tenant_ids_defensively() -> None:
    unsafe = " tenant/<script>alert(1)</script>" * 4
    tenant = _safe_tenant_id(unsafe)
    assert len(tenant) <= 64
    assert "/" not in tenant
    assert "<" not in tenant
    assert ">" not in tenant


def test_rate_limiter_clamps_environment_limits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DUECARE_RATE_LIMIT_PER_MIN", "100000000")
    monkeypatch.setenv("DUECARE_CONCURRENCY_PER_TENANT", "0")
    monkeypatch.setenv("DUECARE_RATE_LIMIT_MAX_TENANTS", "100000000")

    middleware = RateLimitMiddleware(FastAPI())

    assert middleware._rpm == 10_000
    assert middleware._concurrency == 1
    assert middleware._max_tenants == 100_000


def test_rate_limit_is_per_tenant() -> None:
    """Tenant A exceeding their cap doesn't affect tenant B."""
    app = _build_app(rpm=2)
    client = TestClient(app)
    for _ in range(5):
        client.get("/echo", headers={"X-Tenant-ID": "tenant-a"})
    # Tenant B should still get a clean 200
    r = client.get("/echo", headers={"X-Tenant-ID": "tenant-b"})
    assert r.status_code == 200


def test_concurrency_rejection_does_not_consume_rpm_token() -> None:
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, rpm=2, concurrency=1)
    app.add_middleware(TenancyMiddleware, default_tenant="test-default")
    entered = threading.Event()
    release = threading.Event()

    @app.get("/hold")
    def hold() -> dict[str, bool]:
        entered.set()
        release.wait(timeout=2)
        return {"ok": True}

    @app.get("/echo")
    def echo() -> dict[str, bool]:
        return {"ok": True}

    client = TestClient(app)
    accepted_statuses: list[int] = []
    worker = threading.Thread(
        target=lambda: accepted_statuses.append(
            client.get("/hold", headers={"X-Tenant-ID": "tenant-a"}).status_code
        ),
    )
    worker.start()
    assert entered.wait(timeout=2)

    rejected = client.get("/echo", headers={"X-Tenant-ID": "tenant-a"})
    release.set()
    worker.join(timeout=2)

    assert accepted_statuses == [200]
    assert rejected.status_code == 429
    assert client.get("/echo", headers={"X-Tenant-ID": "tenant-a"}).status_code == 200


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
