"""Intent-aware benign split (roadmap P4 + P5) — under-refusal lift vs over-refusal cost.

The safety lift is measured over ADVERSARIAL prompts only; BENIGN control prompts (legitimate worker
questions) run through the same arms and feed a SEPARATE over-refusal block via rubric v2's F channel.
The two numbers are never merged. Adversarial-only runs stay byte-identical (no intent tag, no block).
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


sys.path.insert(0, str(_ROOT / "scripts"))
for _src in _ROOT.glob("packages/*/src"):
    sys.path.insert(0, str(_src))
rh = _load("rich_harness_lift", _ROOT / "scripts" / "rich_harness_lift.py")


# ---- intent helpers --------------------------------------------------------------------------------

def test_prompt_intent_defaults_and_fails_closed_to_adversarial():
    assert rh.DEFAULT_INTENT == "adversarial"
    assert rh.prompt_intent({"id": "p"}) == "adversarial"          # unlabeled = adversarial
    assert rh.prompt_intent({"id": "p", "intent": "benign"}) == "benign"
    assert rh.prompt_intent({"id": "p", "intent": "sneaky"}) == "adversarial"   # unknown fails closed
    assert rh._row_intent({"intent": "benign"}) == "benign"
    assert rh._row_intent({}) == "adversarial"


# ---- generation stamps intent (benign only) --------------------------------------------------------

def test_generate_responses_stamps_intent_benign_only(tmp_path):
    prompts = [{"id": "ADV1", "text": "adversarial scheme"},
               {"id": "BEN1", "text": "benign worker question", "intent": "benign"}]
    results_path = tmp_path / "results.jsonl"
    rh.generate_responses(prompts, ["m"], reuse={}, results_path=results_path,
                          generate=lambda _m, _p: "reply", pace=0.0, max_tokens=10,
                          log=lambda _m: None, concurrency=1)
    rows = [json.loads(x) for x in results_path.read_text(encoding="utf-8").splitlines()]
    adv = [r for r in rows if r["prompt_id"] == "ADV1"]
    ben = [r for r in rows if r["prompt_id"] == "BEN1"]
    assert adv and all("intent" not in r for r in adv)             # adversarial rows byte-compatible
    assert ben and all(r["intent"] == "benign" for r in ben)


def test_judge_panel_carries_intent_into_panel_rows(tmp_path):
    results = [
        {"model": "cand", "prompt_id": "ADV1", "arm": "baseline",
         "prompt_text": "q", "response": "r"},
        {"model": "cand", "prompt_id": "BEN1", "arm": "baseline",
         "prompt_text": "q", "response": "r", "intent": "benign"},
    ]
    panel_path = tmp_path / "panel.jsonl"
    rh.judge_panel(results, ["judge-x"], panel_path=panel_path,
                   judge_caller=lambda p, **kw: json.dumps({"A": 10, "B": 8, "C": 8, "D": 5, "E": 5, "score": 36}),
                   pace=0, log=lambda m: None)
    rows = {json.loads(x)["prompt_id"]: json.loads(x)
            for x in panel_path.read_text(encoding="utf-8").splitlines()}
    assert "intent" not in rows["ADV1"]
    assert rows["BEN1"]["intent"] == "benign"


# ---- aggregation: lift is adversarial-only, benign feeds the over-refusal block ---------------------

def _panel_row(model, pid, arm, score, judge="j", *, intent=None, f=None, rubric=None):
    comps = {} if f is None else {"F": f}
    row = {"key": f"{model}|{pid}|{arm}", "model": model, "arm": arm, "prompt_id": pid,
           "judge": judge, "score_0_100": score, "components": comps}
    if intent:
        row["intent"] = intent
    if rubric:
        row["rubric"] = rubric
    return row


def test_aggregate_excludes_benign_from_lift_and_reports_over_refusal_cost():
    panel = []
    # adversarial prompt: the real safety lift signal (baseline 50 -> full 80)
    for arm, s in (("baseline", 50.0), ("harness_core", 70.0), ("harness_full", 80.0)):
        panel.append(_panel_row("m", "ADV1", arm, s, rubric="v2", f=8))
    # a benign prompt with a HUGE score on every arm -- if it leaked into the lift it would distort it
    for arm in rh.ARMS:
        panel.append(_panel_row("m", "BEN1", arm, 100.0, intent="benign", rubric="v2",
                                f={"baseline": 9, "harness_core": 6, "harness_full": 4}[arm]))

    agg = rh.aggregate(panel, ["j"], rubric_version="v2")

    # the lift is computed over the adversarial prompt ONLY (benign 100s did not move it)
    m = agg["models"][0]
    assert m["panel_arm"] == {"baseline": 50.0, "harness_core": 70.0, "harness_full": 80.0}
    assert m["lift_full_vs_baseline"] == 30.0
    assert m["n_prompts"] == 1

    # the over-refusal block: F drops from baseline 9 -> full 4, a cost of 5
    orf = agg["over_refusal"]
    assert orf is not None and orf["has_f_channel"] is True
    row = orf["rows"][0]
    assert row["n_benign_prompts"] == 1
    assert row["f_arm"] == {"baseline": 9.0, "harness_core": 6.0, "harness_full": 4.0}
    assert row["over_refusal_cost_full"] == 5.0
    assert row["over_refusal_cost_core"] == 3.0


def test_aggregate_adversarial_only_run_has_no_over_refusal_block():
    panel = [_panel_row("m", "ADV1", arm, s) for arm, s in
             (("baseline", 50.0), ("harness_core", 70.0), ("harness_full", 80.0))]
    agg = rh.aggregate(panel, ["j"])
    assert agg["over_refusal"] is None                             # byte-identical to pre-intent behavior
    assert agg["models"][0]["lift_full_vs_baseline"] == 30.0


def test_aggregate_v1_benign_reports_score_proxy_without_f():
    panel = [_panel_row("m", "ADV1", arm, s) for arm, s in
             (("baseline", 50.0), ("harness_core", 70.0), ("harness_full", 80.0))]
    for arm, s in (("baseline", 60.0), ("harness_core", 40.0), ("harness_full", 30.0)):
        panel.append(_panel_row("m", "BEN1", arm, s, intent="benign"))   # v1: no F channel
    agg = rh.aggregate(panel, ["j"])
    orf = agg["over_refusal"]
    assert orf is not None and orf["has_f_channel"] is False
    row = orf["rows"][0]
    assert row["score_arm"] == {"baseline": 60.0, "harness_core": 40.0, "harness_full": 30.0}
    assert "over_refusal_cost_full" not in row                     # the real cost needs v2's F


# ---- report renders the split ----------------------------------------------------------------------

def test_build_report_renders_over_refusal_section(tmp_path):
    panel = []
    for arm, s in (("baseline", 50.0), ("harness_core", 70.0), ("harness_full", 80.0)):
        panel.append(_panel_row("m", "ADV1", arm, s, rubric="v2", f=8))
    for arm in rh.ARMS:
        panel.append(_panel_row("m", "BEN1", arm, 90.0, intent="benign", rubric="v2",
                                f={"baseline": 9, "harness_core": 6, "harness_full": 4}[arm]))
    agg = rh.aggregate(panel, ["j"], rubric_version="v2")
    report = rh.build_report(agg, ["j"], out_path=tmp_path / "r.md")
    assert "Intent split - over-refusal cost on benign worker questions" in report
    assert "under-refusal" in report
    assert "never merged" in report
    assert "F channel" in report

    # adversarial-only agg omits the section entirely
    agg_adv = rh.aggregate([_panel_row("m", "ADV1", a, s) for a, s in
                            (("baseline", 50.0), ("harness_core", 70.0), ("harness_full", 80.0))], ["j"])
    report_adv = rh.build_report(agg_adv, ["j"], out_path=tmp_path / "r2.md")
    assert "Intent split" not in report_adv


# ---- the committed benign control set is well-formed and all-benign ---------------------------------

def test_committed_benign_control_set_is_valid_and_all_benign():
    path = _ROOT / "configs" / "duecare" / "benchmarks" / "benign_control_prompts.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    prompts = doc["prompts"]
    assert len(prompts) >= 12
    ids = [p["id"] for p in prompts]
    assert len(ids) == len(set(ids))                               # unique ids
    for p in prompts:
        assert p["intent"] == "benign"
        assert p["text"].strip()
        assert rh.prompt_intent(p) == "benign"
