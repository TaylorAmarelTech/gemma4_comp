"""TestClient unit tests for the hub-side Sentinel scheduler."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest


HUB_APP = Path(__file__).resolve().parents[1] / "apps" / "duecare-ai.com"
if str(HUB_APP) not in sys.path:
    sys.path.insert(0, str(HUB_APP))


@pytest.fixture()
def client_with_token(tmp_path, monkeypatch):
    monkeypatch.setenv("DUECARE_ADMIN_TOKEN", "test-token-abc")
    from app import sentinel as _sentinel
    monkeypatch.setattr(_sentinel, "DATA_DIR", tmp_path)
    monkeypatch.setattr(_sentinel, "STATE_PATH", tmp_path / "sentinel_state.json")
    monkeypatch.setattr(_sentinel, "DRAFTS_PATH", tmp_path / "sentinel_drafts.jsonl")
    monkeypatch.setattr(_sentinel, "SEEN_PATH", tmp_path / "sentinel_seen_urls.json")

    from app.main import create_app
    from fastapi.testclient import TestClient
    yield TestClient(create_app())


def test_sentinel_status_works_without_token(client_with_token):
    r = client_with_token.get("/api/sentinel/status")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "n_queries" in body
    assert body["n_queries"] >= 10
    assert "queries" in body


def test_sentinel_queries_lists_default_set(client_with_token):
    r = client_with_token.get("/api/sentinel/queries")
    assert r.status_code == 200
    slugs = {q["slug"] for q in r.json()["queries"]}
    assert "new_ilo_conventions" in slugs
    assert "trafficking_court_cases" in slugs
    assert "ngo_advisories" in slugs


def test_sentinel_trigger_requires_token(client_with_token):
    r = client_with_token.post("/api/sentinel/trigger/new_ilo_conventions")
    assert r.status_code in (401, 403)


def test_sentinel_run_due_requires_token(client_with_token):
    r = client_with_token.post("/api/sentinel/run-due")
    assert r.status_code in (401, 403)


def test_sentinel_drafts_requires_token(client_with_token):
    r = client_with_token.get("/api/sentinel/drafts")
    assert r.status_code in (401, 403)


def test_sentinel_trigger_returns_error_without_searxng(client_with_token):
    r = client_with_token.post(
        "/api/sentinel/trigger/new_ilo_conventions?token=test-token-abc"
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False
    assert "SEARXNG" in (body.get("error") or "").upper()


def test_sentinel_admin_page_requires_token(client_with_token):
    r = client_with_token.get("/sentinel")
    assert r.status_code in (401, 403)


def test_sentinel_admin_page_renders_with_token(client_with_token):
    r = client_with_token.get("/sentinel?token=test-token-abc")
    assert r.status_code == 200
    assert "Sentinel" in r.text
    assert "new_ilo_conventions" in r.text
