"""Tests for PromptValidator and DocumentQuizGenerator."""

from __future__ import annotations

from duecare.tasks.generators.test_validator import PromptValidator
from duecare.tasks.generators.document_quiz import DocumentQuizGenerator


class TestPromptValidator:
    def test_valid_prompt_passes(self):
        v = PromptValidator()
        r = v.validate_prompt({
            "id": "test1",
            "text": "My agency charges 50000 PHP recruitment fee for domestic workers.",
            "category": "business_framed_exploitation",
        })
        assert r.valid
        assert len(r.issues) == 0

    def test_short_prompt_fails(self):
        v = PromptValidator()
        r = v.validate_prompt({"id": "short", "text": "Hi", "category": "unknown"})
        assert not r.valid
        assert any("too_short" in i for i in r.issues)

    def test_empty_text_fails(self):
        v = PromptValidator()
        r = v.validate_prompt({"id": "empty", "text": "", "category": "unknown"})
        assert not r.valid
        assert "missing_text" in r.issues

    def test_pii_detected(self):
        v = PromptValidator()
        r = v.validate_prompt({
            "id": "pii",
            "text": "Contact worker at maria@example.com about recruitment fee issues.",
            "category": "victim_revictimization",
        })
        assert not r.valid
        assert "contains_pii" in r.issues

    def test_duplicate_detected_in_batch(self):
        v = PromptValidator()
        prompts = [
            {"id": "a", "text": "Agency charges excessive recruitment fee to workers going overseas.", "category": "bfe"},
            {"id": "b", "text": "Agency charges excessive recruitment fee to workers going overseas.", "category": "bfe"},
        ]
        report = v.validate_batch(prompts)
        assert report.invalid_count == 1
        assert "duplicate" in report.issues_by_type

    def test_batch_report_counts(self):
        v = PromptValidator()
        prompts = [
            {"id": "good", "text": "My agency charges 50000 PHP recruitment fee.", "category": "bfe"},
            {"id": "bad", "text": "Hi", "category": "unknown"},
        ]
        report = v.validate_batch(prompts)
        assert report.total == 2
        assert report.valid_count == 1
        assert report.invalid_count == 1
        assert len(report.valid_prompts) == 1
        assert len(report.invalid_prompts) == 1


class TestDocumentQuizGenerator:
    def test_generates_quizzes(self):
        gen = DocumentQuizGenerator()
        prompts = [{"id": "t1", "text": "test", "category": "bfe"}]
        quizzes = gen.generate(prompts, n_variations=3, seed=42)
        assert len(quizzes) == 3
        for q in quizzes:
            assert "text" in q
            assert "metadata" in q
            assert "quiz_type" in q["metadata"]
            assert "grounding_law" in q["metadata"]

    def test_deterministic(self):
        gen = DocumentQuizGenerator()
        prompts = [{"id": "t1", "text": "test", "category": "bfe"}]
        r1 = gen.generate(prompts, n_variations=2, seed=42)
        r2 = gen.generate(prompts, n_variations=2, seed=42)
        assert r1[0]["text"] == r2[0]["text"]

    def test_grounding_facts_present(self):
        gen = DocumentQuizGenerator()
        prompts = [{"id": "t1", "text": "test", "category": "bfe"}]
        quizzes = gen.generate(prompts, n_variations=5, seed=42)
        for q in quizzes:
            assert q["metadata"]["grounding_law"]
            assert q["metadata"]["grounding_fact"]
            assert q.get("graded_responses", {}).get("best")
