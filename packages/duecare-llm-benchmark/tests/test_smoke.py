"""Smoke tests for duecare-llm-benchmark."""
from __future__ import annotations


def test_imports() -> None:
    from duecare import benchmark
    assert hasattr(benchmark, "list_sets")
    assert hasattr(benchmark, "load_set")
    assert hasattr(benchmark, "score_row")
    assert hasattr(benchmark, "aggregate")


def test_smoke_25_loads() -> None:
    from duecare.benchmark import list_sets, load_set
    sets = list_sets()
    slugs = {s.slug for s in sets}
    assert "smoke_25" in slugs
    rows = load_set("smoke_25")
    assert len(rows) == 25
    for r in rows:
        assert r["id"].startswith("smoke_")
        assert r["expected_verdict"] in ("block", "review", "pass")
        assert isinstance(r["expected_severity_min"], int)


def test_score_row_and_aggregate() -> None:
    from duecare.benchmark import score_row, aggregate
    expected = {"expected_verdict": "block", "expected_severity_min": 7,
                "expected_signals": ["passport_id"]}
    result = {"verdict": "block", "severity": 8,
              "matched_signals": [{"name": "passport_id"}]}
    sr = score_row(expected, result)
    assert sr["verdict_ok"] is True
    assert sr["severity_ok"] is True
    assert sr["row_pass"] is True
    agg = aggregate([sr])
    assert agg["n"] == 1
    assert agg["pass_rate"] == 1.0
