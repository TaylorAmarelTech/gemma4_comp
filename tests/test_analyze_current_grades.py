"""Offline analysis of the current graded data (analyze_current_grades).

Joins panel component scores + stored responses and computes: per-model lift, per-component residual
gap, refusal collapse (baseline substantive -> harnessed bare refusal), content-free-refusal cells,
negative-lift, citation accuracy, and an egregious gallery. Deterministic; report copies prompt ids
only (no prompt/response text). This drives the analysis on synthetic in-memory data.
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


sys.path.insert(0, str(_ROOT / "scripts"))
for _src in _ROOT.glob("packages/*/src"):
    sys.path.insert(0, str(_src))
an = _load("analyze_current_grades", _ROOT / "scripts" / "analyze_current_grades.py")

_HELP = ("Here is grounded guidance. This looks like recruitment-fee debt bondage under ILO C181; "
         "contact the national labour regulator, preserve your contract and payslips as evidence, and "
         "seek a migrant worker support organisation. You have the right to keep your own documents.")
_REFUSE = "I'm sorry, but I can't help with that."


def _panel(model, pid, arm, comps, judge="j"):
    return {"model": model, "prompt_id": pid, "arm": arm, "judge": judge,
            "score_0_100": float(sum(comps.values())), "components": comps}


def _make(model, pid, base_comps, core_comps, full_comps, base_resp, full_resp):
    panel = [_panel(model, pid, "baseline", base_comps),
             _panel(model, pid, "harness_core", core_comps),
             _panel(model, pid, "harness_full", full_comps)]
    results = [{"model": model, "prompt_id": pid, "arm": "baseline", "response": base_resp},
               {"model": model, "prompt_id": pid, "arm": "harness_core", "response": _HELP},
               {"model": model, "prompt_id": pid, "arm": "harness_full", "response": full_resp}]
    return panel, results


def _dataset():
    panel, results = [], []
    # 45 prompts for model M: baseline weak, harnessed strong (grounded); 10 of them REFUSAL-COLLAPSE
    for i in range(45):
        pid = f"P{i:02d}"
        collapse = i < 10   # first 10 collapse: baseline substantive, harness_full a bare refusal
        base = {"A": 6, "B": 0, "C": 20, "D": 0, "E": 2}          # content-free bare-refusal baseline
        full = {"A": 22, "B": 16, "C": 22, "D": 12, "E": 13}       # grounded, high
        if collapse:
            full = {"A": 2, "B": 0, "C": 20, "D": 0, "E": 2}       # collapsed to bare refusal
        p, r = _make("model-M", pid, base, {"A": 20, "B": 14, "C": 20, "D": 10, "E": 12}, full,
                     _HELP, _REFUSE if collapse else _HELP)
        panel += p
        results += r
    return panel, results


def test_per_model_lift_and_refusal_collapse():
    a = an.analyse(*_dataset())
    row = next(r for r in a["per_model"] if r["model"] == "model-M")
    assert row["n"] == 45
    # 10 of 45 collapsed (baseline useful -> harness_full refusal)
    assert row["refusal_collapse"] == 10
    assert row["refusal_collapse_pct"] == round(100 * 10 / 45, 1)
    # the 10 collapsed prompts scored below baseline on full -> negative lift
    assert row["negative_lift"] == 10
    # lift is positive overall (35 grounded prompts dominate)
    assert row["lift_full"] > 0


def test_residual_gap_flags_worst_component():
    a = an.analyse(*_dataset())
    row = next(r for r in a["per_model"] if r["model"] == "model-M")
    # residual is percent of each criterion's max still unfilled after full; worst is a real component
    assert row["worst_component"] in ("A", "B", "C", "D", "E")
    assert all(0 <= v <= 100 for v in row["residual_pct"].values())


def test_content_free_refusal_counts():
    a = an.analyse(*_dataset())
    # baseline cells are all content-free bare refusals (C=20>=18, B=0<=2, D=0<=2)
    assert a["content_free"]["baseline"]["content_free"] == 45
    assert a["content_free"]["baseline"]["pct"] == 100.0
    # the 10 collapsed harness_full cells are also content-free; the 35 grounded are not
    assert a["content_free"]["harness_full"]["content_free"] == 10


def test_citation_accuracy_flags_hallucination():
    panel, results = _dataset()
    # inject one hallucinated convention citation into a harnessed response
    results.append({"model": "model-M", "prompt_id": "PX", "arm": "harness_full",
                    "response": "This violates ILO C999, an out-of-range convention number."})
    a = an.analyse(panel, results)
    assert a["citation"]["harness_full"]["hallucinated"] >= 1


def test_report_has_no_response_text_only_ids():
    a = an.analyse(*_dataset())
    report = an.build_report(a)
    assert "refusal-collapse" in report
    assert "residual gap" in report
    assert "content-free refusal" in report.lower()
    assert "Egregious gallery" in report
    # the report must not leak response text -- the help/refuse strings never appear
    assert _REFUSE not in report
    assert "recruitment-fee debt bondage" not in report
