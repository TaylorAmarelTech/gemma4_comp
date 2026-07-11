"""Full-results analyzer: aggregate() joins per-judge panel rows into per-(model,arm) means and reports the
lifts, the helps/hurts tail, and full-vs-core -- the honest current read over whatever is graded so far."""
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


sys.path.insert(0, str(_ROOT / "scripts"))
a = _load("analyze_full_results", _ROOT / "scripts" / "analyze_full_results.py")


def _row(pid, arm, score, comps=None):
    return {"model": "gemma4:31b", "prompt_id": pid, "arm": arm, "score_0_100": score,
            "components": comps or {}}


def test_aggregate_computes_lift_and_hurt_tail():
    rows = [
        # p1: harness helps (40 -> 90), full a touch below core (88)
        _row("p1", "baseline", 40, {"A": 5}), _row("p1", "harness_core", 90, {"A": 14}),
        _row("p1", "harness_full", 88),
        # p2: harness HURTS (60 -> 55)
        _row("p2", "baseline", 60), _row("p2", "harness_core", 55),
    ]
    agg = a.aggregate(rows)
    m = agg["per_model"][0]
    assert m["model"] == "gemma4:31b" and m["n_pair"] == 2
    assert m["baseline"] == 50.0 and m["core"] == 72.5           # (40+60)/2, (90+55)/2
    assert m["lift_core"] == 22.5                                 # ((90-40)+(55-60))/2 = (50-5)/2
    assert m["helps"] == 1 and m["hurts"] == 1 and m["hurt_worst"] == -5.0
    assert m["full_minus_core"] == -2.0                           # only p1 has full: 88-90
    assert m["components"]["A"] == 9.0                            # 14-5
    assert agg["graded_prompt_ids"] == 2


def test_aggregate_skips_unpaired_and_nonnumeric():
    rows = [_row("q1", "baseline", 30), _row("q1", "harness_core", "N/A"),   # non-numeric score dropped
            {"model": "gemma4:31b", "prompt_id": "q2", "arm": "baseline"}]    # no score
    agg = a.aggregate(rows)
    # q1 core is non-numeric -> not paired; q2 has no score -> nothing paired
    assert agg["per_model"] == [] or all(r["n_pair"] == 0 for r in agg["per_model"])


def test_render_states_coverage_against_registry():
    rows = [_row("p1", "baseline", 40), _row("p1", "harness_core", 90)]
    out = a.render(a.aggregate(rows), registry=74640, today="2026-07-11")
    assert "of the 74,640-prompt registry" in out and "credit-gated" in out
