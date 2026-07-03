"""Per-framing lift (the pretext set's payoff).

The pretext / money-laundering prompts carry a `framing` label (journalist, consultant, operator, ...).
This threads framing through generation -> judging -> aggregation so the board can report the lift per
framing -- does the harness fire on a third-party wrapper as well as on an operator-voice ask? Untagged
prompts are unaffected (backward compatible).
"""
from __future__ import annotations

import importlib.util
import json
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
rh = _load("rich_harness_lift", _ROOT / "scripts" / "rich_harness_lift.py")


def test_framing_helpers():
    assert rh._prompt_framing({"framing": "journalist"}) == "journalist"
    assert rh._prompt_framing({"id": "x"}) is None
    assert rh._row_framing({"framing": "consultant_for_client"}) == "consultant_for_client"
    assert rh._row_framing({}) is None


def test_generation_stamps_framing(tmp_path):
    prompts = [{"id": "P1", "text": "operator ask", "framing": "operator"},
               {"id": "P2", "text": "plain scheme"}]  # no framing
    results = tmp_path / "results.jsonl"
    rh.generate_responses(prompts, ["m"], reuse={}, results_path=results,
                          generate=lambda _m, _p: "reply", pace=0.0, max_tokens=10,
                          log=lambda _m: None, concurrency=1)
    rows = [json.loads(x) for x in results.read_text(encoding="utf-8").splitlines()]
    assert all(r["framing"] == "operator" for r in rows if r["prompt_id"] == "P1")
    assert all("framing" not in r for r in rows if r["prompt_id"] == "P2")


def test_judge_panel_carries_framing(tmp_path):
    results = [{"model": "cand", "prompt_id": "P1", "arm": "baseline", "prompt_text": "q",
                "response": "r", "framing": "journalist"},
               {"model": "cand", "prompt_id": "P2", "arm": "baseline", "prompt_text": "q", "response": "r"}]
    panel = tmp_path / "panel.jsonl"
    rh.judge_panel(results, ["judge-x"], panel_path=panel,
                   judge_caller=lambda p, **kw: json.dumps({"A": 10, "B": 8, "C": 8, "D": 5, "E": 5, "score": 36}),
                   pace=0, log=lambda m: None)
    rows = {json.loads(x)["prompt_id"]: json.loads(x) for x in panel.read_text(encoding="utf-8").splitlines()}
    assert rows["P1"]["framing"] == "journalist"
    assert "framing" not in rows["P2"]


def _panel_row(pid, arm, score, framing=None, judge="j", model="m"):
    row = {"key": f"{model}|{pid}|{arm}", "model": model, "arm": arm, "prompt_id": pid,
           "judge": judge, "score_0_100": score, "components": {}}
    if framing:
        row["framing"] = framing
    return row


def test_aggregate_reports_per_framing_lift():
    panel = []
    # journalist framing: weak lift (baseline 40 -> full 55, +15); operator framing: strong (+40)
    for arm, s in (("baseline", 40.0), ("harness_core", 50.0), ("harness_full", 55.0)):
        panel.append(_panel_row("J1", arm, s, framing="journalist"))
    for arm, s in (("baseline", 40.0), ("harness_core", 75.0), ("harness_full", 80.0)):
        panel.append(_panel_row("O1", arm, s, framing="operator"))
    agg = rh.aggregate(panel, ["j"])
    bf = agg["by_framing"]
    assert bf is not None
    by = {r["framing"]: r for r in bf["rows"]}
    assert by["journalist"]["lift_full_vs_baseline"] == 15.0
    assert by["operator"]["lift_full_vs_baseline"] == 40.0
    # weakest-lift framing sorts first (the residual gap surfaces at the top)
    assert bf["rows"][0]["framing"] == "journalist"


def test_aggregate_no_framing_rows_is_none():
    panel = [_panel_row("P1", a, s) for a, s in
             (("baseline", 50.0), ("harness_core", 70.0), ("harness_full", 80.0))]
    assert rh.aggregate(panel, ["j"])["by_framing"] is None


def test_report_renders_framing_section(tmp_path):
    panel = []
    for arm, s in (("baseline", 40.0), ("harness_core", 50.0), ("harness_full", 55.0)):
        panel.append(_panel_row("J1", arm, s, framing="journalist"))
    agg = rh.aggregate(panel, ["j"])
    report = rh.build_report(agg, ["j"], out_path=tmp_path / "r.md")
    assert "Per-framing lift" in report
    assert "journalist" in report
    # a framing-free run omits the section
    plain = [_panel_row("P1", a, s) for a, s in
             (("baseline", 50.0), ("harness_core", 70.0), ("harness_full", 80.0))]
    assert "Per-framing lift" not in rh.build_report(rh.aggregate(plain, ["j"]), ["j"], out_path=tmp_path / "r2.md")
