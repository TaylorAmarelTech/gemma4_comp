"""analyze_dips: find harness regressions + low-lift valleys + the weakest dimension, as a worklist."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location("analyze_dips", _ROOT / "scripts" / "analyze_dips.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["analyze_dips"] = mod
    spec.loader.exec_module(mod)
    return mod


d = _load()


def _row(pid, arm, score, comps=None):
    return {"model": "gemma4:31b", "prompt_id": pid, "arm": arm, "score_0_100": score, "components": comps or {}}


def test_finds_regressions_valleys_and_weakest_dimension():
    rows = []
    # p1: strong lift (win); p2: HURTS (regression); p3/p4: low-lift valley in cat "weak"
    rows += [_row("p1", "baseline", 30, {"A": 2, "C": 9}), _row("p1", "harness_core", 90, {"A": 18, "C": 10})]
    rows += [_row("p2", "baseline", 70, {"A": 8}), _row("p2", "harness_core", 60, {"A": 6})]  # -10 regression
    for i in range(20):  # a valley category with tiny lift, enough n to rank
        rows += [_row(f"w{i}", "baseline", 50), _row(f"w{i}", "harness_core", 52)]
    meta = {"p1": {"category": "strong"}, "p2": {"category": "adversarial"}}
    meta.update({f"w{i}": {"category": "weak"} for i in range(20)})
    dips = d.find_dips(rows, meta, "gemma4:31b")
    # regression surfaced with its category
    assert any(r["prompt_id"] == "p2" and r["lift"] == -10.0 and r["category"] == "adversarial"
               for r in dips["regressions"])
    # the low-lift 'weak' category is the top valley (n>=20)
    assert dips["valley_categories"][0]["value"] == "weak"
    # C (refusal) barely moved (+1) vs A (+16) -> weakest is C
    assert dips["weakest_dimension"] == "C"


def test_no_regressions_when_harness_never_hurts():
    rows = [d_ for i in range(3) for d_ in (_row(f"p{i}", "baseline", 40), _row(f"p{i}", "harness_core", 80))]
    dips = d.find_dips(rows, {}, "gemma4:31b")
    assert dips["regressions"] == []
    assert "No regressions" in d.render(dips)


def test_render_has_worklist_actions_and_full_sweep_rationale():
    rows = [_row("p1", "baseline", 70), _row("p1", "harness_core", 60)]
    out = d.render(d.find_dips(rows, {"p1": {"category": "x"}}, "gemma4:31b"))
    assert "Training action" in out
    assert "why the full sweep must finish" in out.lower()
