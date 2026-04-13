"""Tests for RAG store and report generator."""

from __future__ import annotations

from src.demo.rag import RAGStore
from src.demo.report_generator import generate_html_report


class TestRAGStore:
    def test_loads_from_configs(self):
        store = RAGStore.from_configs()
        assert len(store) > 50  # Should have 100+ entries

    def test_retrieves_relevant_context(self):
        store = RAGStore.from_configs()
        context = store.retrieve("recruitment fee Philippines domestic worker")
        assert len(context) > 0
        assert "fee" in context.lower() or "recruit" in context.lower()

    def test_retrieves_corridor_context(self):
        store = RAGStore.from_configs()
        context = store.retrieve("passport confiscation Saudi Arabia kafala")
        assert len(context) > 0

    def test_returns_empty_for_unrelated(self):
        store = RAGStore.from_configs()
        context = store.retrieve("quantum physics dark matter", min_overlap=5)
        assert context == ""

    def test_top_k_limits_results(self):
        store = RAGStore.from_configs()
        ctx3 = store.retrieve("recruitment fee worker", top_k=3)
        ctx1 = store.retrieve("recruitment fee worker", top_k=1)
        assert len(ctx1) <= len(ctx3)

    def test_entries_have_content_and_type(self):
        store = RAGStore.from_configs()
        for entry in store._entries[:5]:
            assert "content" in entry
            assert "type" in entry
            assert len(entry["content"]) > 10


class TestReportGenerator:
    def test_generates_html(self):
        findings = {
            "model": {"name": "test-model"},
            "evaluation_date": "2026-04-12",
            "summary": {
                "n_prompts": 10,
                "mean_score": 0.6,
                "pass_rate": 0.2,
                "refusal_rate": 0.5,
                "grade_distribution": {"best": 0, "good": 2, "neutral": 6, "bad": 1, "worst": 1},
            },
            "results": [
                {"id": "p1", "category": "bfe", "grade": "good", "score": 0.8, "has_refusal": True, "has_legal_ref": True},
                {"id": "p2", "category": "vrv", "grade": "neutral", "score": 0.5, "has_refusal": False, "has_legal_ref": False},
            ],
        }
        html = generate_html_report(findings)
        assert "<!DOCTYPE html>" in html
        assert "DueCare" in html
        assert "test-model" in html
        assert "0.60" in html or "0.6" in html
        assert "Privacy is non-negotiable" in html

    def test_report_includes_all_sections(self):
        findings = {
            "model": {"name": "gemma-4-e2b"},
            "summary": {"n_prompts": 5, "mean_score": 0.5, "pass_rate": 0.2, "refusal_rate": 0.4, "grade_distribution": {}},
            "results": [],
        }
        html = generate_html_report(findings)
        assert "Headline Metrics" in html
        assert "Grade Distribution" in html
        assert "Per-Prompt Results" in html
        assert "Cal. Civ. Code" in html
