"""perdim_interim_goals: large interim-milestone dashboard over the shuffled per-dimension panel."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


g = _load("perdim_interim_goals", _ROOT / "scripts" / "perdim_interim_goals.py")


def _pairs(n, base=40, core=85):
    rows = []
    for i in range(n):
        rows += [{"model": "gemma4:31b", "prompt_id": f"p{i}", "arm": "baseline", "score_0_100": base, "components": {}},
                 {"model": "gemma4:31b", "prompt_id": f"p{i}", "arm": "harness_core", "score_0_100": core, "components": {}}]
    return rows


def test_representativeness_flags_a_narrow_sample():
    cats = {f"p{i}": ("labor_trafficking" if i < 90 else f"cat{i}") for i in range(100)}
    ncat, tcat, gap = g.representativeness({f"p{i}" for i in range(10)}, cats)  # only 'labor_trafficking'
    # narrowness shows in COVERAGE (1 of 11 categories); the share gap is small here only because
    # labor_trafficking also dominates the whole. A real skewed sample (rare category over-drawn)
    # yields a large gap, as the live dashboard shows.
    assert ncat == 1 and tcat == 11 and gap > 5


def test_representativeness_none_without_categories():
    assert g.representativeness({"p0"}, {}) is None
    assert g.representativeness(set(), {"p0": "x"}) is None


def test_ladder_marks_reached_and_pending_with_lift():
    rows = _pairs(30)
    cats = {f"p{i}": "labor_trafficking" for i in range(30)}
    out = g.render(rows, cats, (10, 50), registry=100)
    assert "reached" in out                      # the 10 milestone (< 30 paired) is reached
    assert "10,000" not in out                   # only the milestones we passed appear
    assert "lift +45.0" in out                   # 85 - 40
    assert "paired 30 prompts" in out
    assert "50" in out and "60.0%" in out         # 30/50 progress toward the pending goal


def test_empty_panel_is_handled():
    assert "no paired" in g.render([], {}, (5000,), registry=100)
