"""Regression coverage for the search-safety harness.

The harness intercepts outbound search queries and strips PII before
the query reaches any third-party backend (Brave / Tavily / SearXNG).
These tests pin:
  - the harness contract (name / applied_layers / consumes / emits /
    register_routes)
  - the redaction behavior for each pattern in _REDACTION_PATTERNS
  - the response schema (sanitized / redactions / blocked / mode)
  - that the audit log NEVER contains the raw plaintext query
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from duecare.chat.app import create_app
    app = create_app()
    return TestClient(app)


def test_harness_contract():
    """rule_70 contract: name + applied_layers + consumes + emits +
    register_routes must all exist."""
    from duecare.chat.harnesses import search_safety
    assert search_safety.name == "search_safety"
    assert search_safety.applied_layers == ()
    assert "grep_rule" in search_safety.consumes
    assert "audit_template" in search_safety.emits
    assert callable(search_safety.register_routes)


def test_harness_registered_as_primary():
    """search_safety should be in PRIMARY_HARNESSES so every kernel
    using create_app picks it up automatically."""
    from duecare.chat.harnesses import (
        PRIMARY_HARNESSES, search_safety,
    )
    assert search_safety in PRIMARY_HARNESSES


def test_safety_info_endpoint(client):
    r = client.get("/api/search/safety-info")
    assert r.status_code == 200
    body = r.json()
    assert body["regex_redaction"] is True
    assert "patterns" in body
    assert "email" in body["patterns"]
    assert "passport" in body["patterns"]


def test_redacts_email(client):
    r = client.post("/api/search/sanitize", json={
        "query": "find statutes about employer reaching john.doe@example.com",
        "mode": "strict",
    })
    assert r.status_code == 200
    body = r.json()
    assert "john.doe@example.com" not in body["sanitized"]
    assert "[REDACTED-EMAIL]" in body["sanitized"]
    kinds = [r["kind"] for r in body["redactions"]]
    assert "email" in kinds


def test_redacts_passport(client):
    r = client.post("/api/search/sanitize", json={
        "query": "look up passport AB1234567 retention rules",
        "mode": "strict",
    })
    assert r.status_code == 200
    body = r.json()
    assert "AB1234567" not in body["sanitized"]
    assert any("PASSPORT" in r["replacement"] for r in body["redactions"])


def test_redacts_phone(client):
    r = client.post("/api/search/sanitize", json={
        "query": "call agency at 555-123-4567 for refund",
        "mode": "strict",
    })
    assert r.status_code == 200
    body = r.json()
    assert "555-123-4567" not in body["sanitized"]


def test_redacts_monetary(client):
    r = client.post("/api/search/sanitize", json={
        "query": "agency charged me 32000 PHP placement fee",
        "mode": "strict",
    })
    assert r.status_code == 200
    body = r.json()
    assert "32000 PHP" not in body["sanitized"]
    kinds = [r["kind"] for r in body["redactions"]]
    assert "monetary" in kinds


def test_no_redactions_when_clean(client):
    """A query with no PII should pass through unchanged (no
    false-positive redactions)."""
    r = client.post("/api/search/sanitize", json={
        "query": "ILO Convention 181 fee prohibition migrant worker",
        "mode": "strict",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["sanitized"] == "ILO Convention 181 fee prohibition migrant worker"
    assert body["redactions"] == []
    assert body["blocked"] is False


def test_empty_query_rejected(client):
    r = client.post("/api/search/sanitize", json={"query": "", "mode": "strict"})
    assert r.status_code == 400


def test_response_schema(client):
    """Pin the response shape so the UI can rely on the field names."""
    r = client.post("/api/search/sanitize", json={
        "query": "test query with john@example.com",
        "mode": "strict",
    })
    assert r.status_code == 200
    body = r.json()
    for key in ("sanitized", "redactions", "blocked", "mode",
                  "rephrase_fired", "rephrase_wired"):
        assert key in body, f"missing key in response: {key}"
    if body["redactions"]:
        red = body["redactions"][0]
        for key in ("kind", "original_sha256", "replacement"):
            assert key in red, f"missing key in redaction: {key}"
        # Hash, not plaintext
        assert len(red["original_sha256"]) == 16


def test_audit_logs_no_plaintext(client):
    """The training-log helper should write sha256, not raw text.
    Verifies the safety-gate rule (10_safety_gate.md). This test
    issues a fresh sanitize call with a distinctive synthetic
    plaintext, then asserts that plaintext is NEVER written to
    /kaggle/working/training/search_safety.jsonl (or the dev
    fallback at .duecare-training/)."""
    from pathlib import Path

    # Force a write by calling sanitize with unique markers we can
    # search for after.
    distinctive_plaintexts = [
        "distinctive-email-marker@example-domain.test",
        "AZ9876543",  # passport pattern
        "987-654-3210",  # phone pattern
        "999999 USD",  # monetary
    ]
    composed = "audit-self-check " + " ".join(distinctive_plaintexts)
    r = client.post("/api/search/sanitize", json={
        "query": composed,
        "mode": "strict",
    })
    assert r.status_code == 200, "sanitize call failed; can't audit"

    # Now locate the audit JSONL (prod or dev fallback).
    candidate_dirs = [
        Path("/kaggle/working/training"),
        Path(".duecare-training"),
    ]
    jsonl = None
    for d in candidate_dirs:
        candidate = d / "search_safety.jsonl"
        if candidate.exists():
            jsonl = candidate
            break
    assert jsonl is not None, (
        "no audit log written after sanitize call -- "
        "log_interaction may have failed silently"
    )
    text = jsonl.read_text(encoding="utf-8")
    for p in distinctive_plaintexts:
        assert p not in text, (
            f"audit log leaked plaintext: {p!r} -- safety-gate violation"
        )
