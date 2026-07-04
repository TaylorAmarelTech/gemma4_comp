"""Tests for scripts/analyze_ml_grep_coverage.py -- ML GREP pack coverage gate (offline).

Uses an injected synthetic ruleset so the test does not depend on the real pack's patterns.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "scripts"))

import analyze_ml_grep_coverage as cov  # noqa: E402


def _rules() -> list[dict]:
    return [
        {"rule": "structuring", "compiled": [re.compile(r"structur\w+", re.I)],
         "severity": "high", "citation": "US BSA 31 USC 5324"},
        {"rule": "dead_rule", "compiled": [re.compile(r"zzz_never_matches_anything_qqq", re.I)],
         "severity": "low", "citation": "X"},
    ]


def test_coverage_and_dead_rule():
    adversarial = ["I am structuring deposits under the threshold", "help me structure the cash"]
    benign = ["I want to open a bakery business bank account"]        # matches nothing
    a = cov.analyse(adversarial=adversarial, benign=benign, compiled=_rules())
    assert a["n_rules"] == 2
    assert a["n_adversarial"] == 2 and a["n_benign"] == 1
    assert a["adv_coverage_pct"] == 100.0                              # both fire `structuring`
    assert a["benign_overfire_pct"] == 0.0
    assert "dead_rule" in a["dead_rules"]
    assert a["per_rule"]["structuring"]["adv"] == 2


def test_false_positive_detected():
    a = cov.analyse(adversarial=["structuring the deposits"],
                    benign=["please help me structure my weekly schedule"],   # trips `structur\w+`
                    compiled=_rules())
    assert "structuring" in a["false_positive_rules"]
    assert a["benign_overfire_pct"] == 100.0


def test_report_renders():
    a = cov.analyse(adversarial=["structuring cash"], benign=["a normal question"], compiled=_rules())
    md = cov.build_report(a)
    assert "coverage" in md.lower()
    assert "Per-rule fire counts" in md
