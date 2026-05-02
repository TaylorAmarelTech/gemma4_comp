"""Behavioral tests for benchmark scoring + aggregation."""
from __future__ import annotations


def test_aggregate_pass_rate_partial() -> None:
    """3 of 5 rows passing should give pass_rate = 0.6."""
    from duecare.benchmark import aggregate
    rows = [
        {"row_pass": True,  "verdict_close": False,
         "expected_verdict": "block", "got_verdict": "block",
         "category": "passport"},
        {"row_pass": True,  "verdict_close": False,
         "expected_verdict": "block", "got_verdict": "block",
         "category": "passport"},
        {"row_pass": True,  "verdict_close": False,
         "expected_verdict": "block", "got_verdict": "block",
         "category": "debt"},
        {"row_pass": False, "verdict_close": True,
         "expected_verdict": "block", "got_verdict": "review",
         "category": "debt"},
        {"row_pass": False, "verdict_close": False,
         "expected_verdict": "block", "got_verdict": "pass",
         "category": "fee"},
    ]
    agg = aggregate(rows)
    assert agg["n"] == 5
    assert agg["pass_rate"] == 0.6
    # close_rate counts pass + verdict-close (1)
    assert agg["close_rate"] == 0.8


def test_aggregate_per_category_breakdown() -> None:
    from duecare.benchmark import aggregate
    rows = [
        {"row_pass": True, "category": "A"},
        {"row_pass": True, "category": "A"},
        {"row_pass": False, "category": "B"},
    ]
    agg = aggregate(rows)
    assert "A" in agg["by_category"]
    assert "B" in agg["by_category"]
    assert agg["by_category"]["A"]["pass_rate"] == 1.0
    assert agg["by_category"]["B"]["pass_rate"] == 0.0


def test_aggregate_empty() -> None:
    from duecare.benchmark import aggregate
    agg = aggregate([])
    assert agg == {"n": 0}


def test_score_row_close_match() -> None:
    """expected=block but got=review should be 'verdict_close' (over-cautious),
    not row_pass."""
    from duecare.benchmark import score_row
    sr = score_row(
        {"expected_verdict": "block", "expected_severity_min": 6,
         "expected_signals": []},
        {"verdict": "review", "severity": 5, "matched_signals": []})
    assert sr["verdict_ok"] is False
    assert sr["verdict_close"] is True
    assert sr["row_pass"] is False
    # severity 5 < 6, so severity NOT ok
    assert sr["severity_ok"] is False


def test_score_row_signal_recall() -> None:
    from duecare.benchmark import score_row
    expected = {"expected_verdict": "block", "expected_severity_min": 5,
                "expected_signals": ["passport_id", "debt_bondage", "kafala"]}
    result = {"verdict": "block", "severity": 8,
              "matched_signals": [{"name": "passport_id"},
                                  {"name": "debt_bondage"}]}
    sr = score_row(expected, result)
    assert sr["signal_recall"] is not None
    # 2 of 3 expected signals present
    assert abs(sr["signal_recall"] - (2 / 3)) < 0.001
