"""Tests for scripts/analyze_trafficking_grep_coverage.py -- primary GREP coverage gate (offline).

Injected synthetic rules so the test does not depend on the live 451-rule pack. The matcher is a
faithful mirror of harness._grep_call (ANY-match by default, min_capture_value, all_required), so these
pin exactly that behaviour.
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _src in _ROOT.glob("packages/*/src"):
    sys.path.insert(0, str(_src))
sys.path.insert(0, str(_ROOT / "scripts"))

import analyze_trafficking_grep_coverage as tc  # noqa: E402

RULES = [
    {"rule": "kw", "patterns": [r"passport\s+retention"], "severity": "high"},
    {"rule": "dead", "patterns": [r"zzz_never_matches_qqq"], "severity": "critical"},
    {"rule": "apr", "patterns": [r"(\d+)\s*%\s*apr"], "severity": "high", "min_capture_value": 30},
    {"rule": "both", "patterns": [r"\bfee\b", r"\bdeducted\b"], "severity": "medium", "all_required": True},
    {"rule": "badregex", "patterns": ["("], "severity": "low"},   # uncompilable -> empty -> dead
]


def test_fired_rules_any_match_min_capture_all_required():
    c = tc.compile_rules(RULES)
    hi = tc.fired_rules("my passport retention issue, 40% apr, a fee was deducted", c)
    assert hi == {"kw", "apr", "both"}
    lo = tc.fired_rules("just a 20% apr loan, nothing else", c)     # apr below the 30 threshold
    assert lo == set()
    partial = tc.fired_rules("there is a fee here", c)               # 'both' needs 'deducted' too
    assert "both" not in partial


def test_analyse_dead_and_coverage():
    prompts = ["passport retention and 40% apr and fee deducted", "a totally unrelated sentence"]
    a = tc.analyse(prompts=prompts, benign=[], rules=RULES)
    assert a["n_rules"] == 5
    assert "dead" in a["dead_rules"] and "badregex" in a["dead_rules"]
    assert "badregex" in a["empty_pattern_rules"]
    assert a["coverage_pct"] == 50.0            # first prompt fires, second doesn't
    assert a["dead_by_severity"].get("critical") == 1   # the never-firing 'dead' rule


def test_report_renders():
    a = tc.analyse(prompts=["passport retention"], benign=["a benign question about fees"], rules=RULES)
    md = tc.build_report(a)
    assert "never fire on this promptset" in md
    assert "Most-fired rules" in md
