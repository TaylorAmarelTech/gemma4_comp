"""Tests for scripts/four_arm_eval.py -- the Phase 3 four-arm evaluator (CPU-safe core only).

The GPU run() path (load adapter, generate trained C/D) is not exercised; these cover the
panel aggregation, the four-arm table (internalisation + stacking), the report, and prompt pairing.
"""
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


fa = _load("four_arm_eval", _ROOT / "scripts" / "four_arm_eval.py")


def _panel(stock_a, stock_b, trained_c, trained_d, pids=("p1", "p2")):
    rows = []
    for pid in pids:
        for model, arm, s in [("stock", "baseline", stock_a), ("stock", "harness_full", stock_b),
                              ("trained", "baseline", trained_c), ("trained", "harness_full", trained_d)]:
            for j in ("j1", "j2"):
                rows.append({"model": model, "prompt_id": pid, "arm": arm, "judge": j, "score_0_100": s})
    return rows


def test_four_arm_table_computes_internalisation_and_stacking():
    # stock A=40 B=90 (lift 50); trained C=70 D=95 -> internalised 30/50=0.6, stacks (95>=90)
    t = fa.four_arm_table(_panel(40, 90, 70, 95), "stock", "trained")
    assert t["n"] == 2
    assert t["arms"] == {"A_stock_off": 40.0, "B_stock_on": 90.0, "C_trained_off": 70.0, "D_trained_on": 95.0}
    assert t["internalisation"] == 30.0
    assert t["internalised_frac"] == 0.6
    assert t["harness_lift_stock"] == 50.0
    assert t["harness_lift_trained"] == 25.0
    assert t["total"] == 55.0
    assert t["stacks_vs_stock_harness"] is True
    assert t["harness_still_helps_trained"] is True


def test_four_arm_table_empty_when_trained_missing():
    panel = [{"model": "stock", "prompt_id": "p1", "arm": "baseline", "judge": "j", "score_0_100": 40},
             {"model": "stock", "prompt_id": "p1", "arm": "harness_full", "judge": "j", "score_0_100": 90}]
    t = fa.four_arm_table(panel, "stock", "trained")
    assert t["n"] == 0 and t["issues"]


def test_render_report_variants():
    empty = fa.render_report({"n": 0, "issues": ["none yet"]}, generated="t", sha="s")
    assert "No paired data yet" in empty
    t = fa.four_arm_table(_panel(40, 90, 70, 95), "stock", "trained")
    md = fa.render_report(t, generated="t", sha="abc1234")
    assert "Four-arm evaluation" in md and "internalisation" in md and "abc1234" in md
    assert "| C | trained | off | 70.0 |" in md


def test_stock_prompts_requires_both_arms_and_text():
    board_panel = [
        {"model": "m", "prompt_id": "p1", "arm": "baseline", "judge": "j", "score_0_100": 1},
        {"model": "m", "prompt_id": "p1", "arm": "harness_full", "judge": "j", "score_0_100": 2},
        {"model": "m", "prompt_id": "p2", "arm": "baseline", "judge": "j", "score_0_100": 1},  # one arm only
    ]
    board_results = [{"model": "m", "prompt_id": "p1", "arm": "baseline", "prompt_text": "hello", "response": "x"}]
    out = fa._stock_prompts(board_panel, board_results, "m", 0)
    assert out == [{"id": "p1", "text": "hello"}]   # p1 has both arms + text; p2 excluded
