"""Tests for the hub's per-IP rate limiting (app/ratelimit.py).

The public mutation endpoints are unauthenticated by design, so the
limiter is the abuse control: these tests pin the 429 behavior, the
window reset arithmetic, per-client isolation via X-Forwarded-For,
read-path exemption, and the env knob (including its fail-safe parse).
"""
from __future__ import annotations

import pathlib
import tempfile

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.ratelimit import (
    DEFAULT_LIMIT,
    DEFAULT_WINDOW_SECONDS,
    LIMITED_PREFIXES,
    RateLimitMiddleware,
    parse_rate_limit_env,
)

AT = chr(64)  # guaranteed-ASCII '@' (avoid homoglyph traps in source)


def _client(monkeypatch, rate: str) -> TestClient:
    monkeypatch.setenv("DUECARE_RATE_LIMIT", rate)
    return TestClient(create_app(
        data_dir=pathlib.Path(tempfile.mkdtemp(prefix="ratelimit-test-"))))


def _subscribe(client: TestClient, headers: dict | None = None):
    return client.post(
        "/api/newsletter/subscribe",
        json={"email": "ngo" + AT + "example.org", "topics": ["PH-HK"],
              "role": "caseworker", "consent_to_outreach": True},
        headers=headers or {},
    )


def test_limit_returns_429_with_retry_after(monkeypatch):
    client = _client(monkeypatch, "3/60")
    for _ in range(3):
        assert _subscribe(client).status_code == 200
    r = _subscribe(client)
    assert r.status_code == 429
    body = r.json()
    assert body["error"] == "rate_limited"
    assert body["retry_after_seconds"] >= 1
    assert int(r.headers["Retry-After"]) >= 1


def test_reads_are_never_limited(monkeypatch):
    client = _client(monkeypatch, "2/60")
    for _ in range(6):
        assert client.get("/api/outreach/gaps").status_code == 200


def test_window_resets(monkeypatch):
    """Unit-test the window arithmetic with a synthetic clock."""
    limiter = RateLimitMiddleware(app=None, limit=2, window_seconds=10)
    assert limiter.check("ip|/api/hub/signals", now=100.0) is None
    assert limiter.check("ip|/api/hub/signals", now=101.0) is None
    blocked = limiter.check("ip|/api/hub/signals", now=102.0)
    assert blocked is not None and blocked >= 1
    # after the first hit ages out of the window, capacity returns
    assert limiter.check("ip|/api/hub/signals", now=110.5) is None


def test_clients_are_isolated_by_forwarded_ip(monkeypatch):
    client = _client(monkeypatch, "2/60")
    a = {"X-Forwarded-For": "203.0.113.10"}
    b = {"X-Forwarded-For": "203.0.113.99"}
    assert _subscribe(client, a).status_code == 200
    assert _subscribe(client, a).status_code == 200
    assert _subscribe(client, a).status_code == 429  # client A exhausted
    assert _subscribe(client, b).status_code == 200  # client B unaffected


def test_zero_disables(monkeypatch):
    client = _client(monkeypatch, "0")
    for _ in range(8):
        assert _subscribe(client).status_code == 200


def test_outreach_observe_is_covered(monkeypatch):
    """The endpoint that feeds the public priority ranking must be in the
    limited set (and actually 429 when exhausted)."""
    assert any(p == "/api/outreach/observe" for p in LIMITED_PREFIXES)
    client = _client(monkeypatch, "1/60")
    payload = {"gap_id": "fee_cap_ph_hk", "subject": "Re: fees",
               "body": "Still seeing relabelled fees.",
               "sender_email": "ngo" + AT + "example.org"}
    assert client.post("/api/outreach/observe", json=payload).status_code == 200
    assert client.post("/api/outreach/observe", json=payload).status_code == 429


def test_parse_rate_limit_env_fail_safe():
    assert parse_rate_limit_env("") == (DEFAULT_LIMIT, DEFAULT_WINDOW_SECONDS)
    assert parse_rate_limit_env("0") == (0, 0)
    assert parse_rate_limit_env("10/120") == (10, 120)
    assert parse_rate_limit_env("10") == (10, DEFAULT_WINDOW_SECONDS)
    # junk must fall back to limits, never disable them
    assert parse_rate_limit_env("banana") == (DEFAULT_LIMIT, DEFAULT_WINDOW_SECONDS)
    assert parse_rate_limit_env("-5/-9") == (1, 1)
