"""Integration tests for the DueCare demo FastAPI application."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.demo.app import app


@pytest.fixture
def client():
    return TestClient(app)


class TestHealth:
    def test_health_returns_ok(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["rubrics_loaded"] >= 1

    def test_root_returns_html(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "DueCare" in resp.text


class TestDomains:
    def test_domains_lists_trafficking(self, client):
        resp = client.get("/api/v1/domains")
        assert resp.status_code == 200
        domains = resp.json()
        assert len(domains) >= 1
        assert any(d["id"] == "trafficking" for d in domains)


class TestRubrics:
    def test_rubrics_returns_five(self, client):
        resp = client.get("/api/v1/rubrics")
        assert resp.status_code == 200
        rubrics = resp.json()
        assert len(rubrics) == 5
        for r in rubrics:
            assert "name" in r
            assert "n_criteria" in r
            assert r["n_criteria"] > 0


class TestAnalyze:
    def test_analyze_illegal_fee(self, client):
        resp = client.post("/api/v1/analyze", json={
            "text": "I need to pay 50000 PHP recruitment fee to my agency before working in Hong Kong.",
            "context": "chat",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "score" in data
        assert "grade" in data
        assert "action" in data
        assert "legal_refs" in data
        assert "resources" in data
        assert len(data["resources"]) > 0
        assert len(data["legal_refs"]) > 0

    def test_analyze_safe_text(self, client):
        resp = client.post("/api/v1/analyze", json={
            "text": "The weather is nice today.",
            "context": "chat",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["score"] >= 0.0

    def test_analyze_passport_retention(self, client):
        resp = client.post("/api/v1/analyze", json={
            "text": "Give me your passport, I will keep it safe during your employment.",
            "context": "chat",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "score" in data

    def test_analyze_returns_warning_text(self, client):
        resp = client.post("/api/v1/analyze", json={
            "text": "Workers must pay placement fees before departure.",
            "context": "job_posting",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "warning_text" in data


class TestBatch:
    def test_batch_analyze(self, client):
        resp = client.post("/api/v1/batch", json={
            "items": [
                {"text": "Pay 50000 PHP recruitment fee", "context": "chat"},
                {"text": "Normal job posting", "context": "job_posting"},
            ]
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
        assert len(data["results"]) == 2


class TestStats:
    def test_stats_after_analysis(self, client):
        # Run one analysis first
        client.post("/api/v1/analyze", json={
            "text": "Test prompt for stats",
            "context": "chat",
        })
        resp = client.get("/api/v1/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_analyses" in data
        assert data["total_analyses"] >= 1
