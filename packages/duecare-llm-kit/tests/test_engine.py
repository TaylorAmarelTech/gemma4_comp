"""Tests for the DueCare indicator engine port."""
from __future__ import annotations

from duecare.kit.engine import generate_chain, risk_level, scan

# Composite/synthetic worker account (no real PII) that stacks several ILO indicators.
HARMFUL = (
    "The recruitment agency took my passport when I arrived. I still have not been paid my "
    "salary, and they say I must work off the placement fee debt before I can leave. I am not "
    "allowed to leave the compound and my phone was taken."
)
BENIGN = (
    "I started a new job at a local cafe downtown. The pay is fair and arrives on time every "
    "week, my manager is supportive, and my hours are reasonable with weekends free. I feel safe "
    "and can come and go as I like."
)


def test_scan_detects_at_least_four_indicators_on_harmful_example():
    hits = scan(HARMFUL)
    indicators = {h["indicator"] for h in hits}
    assert len(indicators) >= 4, f"expected >=4 distinct indicators, got {sorted(indicators)}"


def test_harmful_example_is_high_risk():
    level, _ = risk_level(scan(HARMFUL))
    assert level == "HIGH"


def test_benign_example_is_not_high_risk():
    level, _ = risk_level(scan(BENIGN))
    assert level != "HIGH"


def test_scan_returns_grounded_hit_shape():
    hits = scan(HARMFUL)
    assert hits, "harmful text should produce hits"
    for h in hits:
        assert set(h) == {"indicator", "label", "snippet", "ilo_ref"}
        assert h["ilo_ref"], "every hit cites an ILO reference"


def test_risk_level_thresholds():
    assert risk_level([])[0] == "LOW"
    assert risk_level([{"indicator": "x"}])[0] == "WATCH"
    assert risk_level([{"indicator": "x"}, {"indicator": "y"}])[0] == "ELEVATED"
    four = [{"indicator": i} for i in "abcd"]
    assert risk_level(four)[0] == "HIGH"


def test_generate_chain_reasons_and_concludes():
    steps = generate_chain(HARMFUL)
    assert steps, "chain should not be empty"
    assert all(isinstance(n, int) and isinstance(text, str) for n, text in steps)
    # numbered contiguously from 1
    assert [n for n, _ in steps] == list(range(1, len(steps) + 1))
    conclusion = steps[-1][1]
    assert "Conclusion" in conclusion and "risk = HIGH" in conclusion


def test_generate_chain_marks_present_indicators():
    steps = generate_chain(HARMFUL)
    present = [t for _, t in steps if "PRESENT" in t]
    assert present, "at least one indicator question should resolve to PRESENT"
