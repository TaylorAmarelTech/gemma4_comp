"""Tests for the QuickFilter enterprise triage component."""

from __future__ import annotations

from src.demo.quick_filter import QuickFilter


def test_triggers_on_recruitment_fee():
    qf = QuickFilter()
    result = qf.check("I need to pay 50000 PHP recruitment fee to the agency")
    assert result.should_trigger
    assert len(result.matched_keywords) > 0
    assert "business_framed_exploitation" in result.category_hints


def test_triggers_on_passport_retention():
    qf = QuickFilter()
    result = qf.check("Give me your passport, I will keep it safe")
    assert result.should_trigger
    assert "victim_revictimization" in result.category_hints


def test_does_not_trigger_on_benign():
    qf = QuickFilter()
    result = qf.check("The weather is nice today")
    assert not result.should_trigger
    assert result.score == 0.0
    assert len(result.matched_keywords) == 0


def test_triggers_on_tagalog():
    qf = QuickFilter()
    result = qf.check("Hindi binayaran ang sahod ko")
    assert result.should_trigger


def test_triggers_on_debt_bondage():
    qf = QuickFilter()
    result = qf.check("You must work off the debt before you can leave")
    assert result.should_trigger


def test_does_not_trigger_on_normal_job():
    qf = QuickFilter()
    result = qf.check("Looking for a software developer with 3 years experience")
    assert not result.should_trigger


def test_performance_under_1ms():
    """QuickFilter must be fast enough for every-message deployment."""
    import time
    qf = QuickFilter()
    texts = [
        "I need to pay recruitment fee",
        "Normal text about software",
        "Passport held by employer",
    ] * 100  # 300 checks

    t0 = time.perf_counter()
    for text in texts:
        qf.check(text)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    per_check_ms = elapsed_ms / len(texts)
    assert per_check_ms < 1.0, f"Too slow: {per_check_ms:.2f}ms/check"
