"""Harness v2 (versioned, opt-in) - the refusal-collapse fix behind --harness-version h2.

Roadmap item 4 (docs/research/benchmark_findings_and_roadmap.md): the harness preamble converts a
correct grounded analysis into a bare refusal on ~14% of prompts for some models. h2 appends the
grounded-response contract (refuse the ask, still deliver indicator + law + resources; never refuse
a legitimate question) to BOTH harnessed preambles. Changed preambles mean h2 responses are NOT
comparable with h1, so h2 gets its own results/panel/pairwise files, tagged rows, filtered
aggregation, and baseline-only reuse - h1 stays the default and byte-identical.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

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

_DOMAIN_SPEC = {
    "display_name": "Synthetic fixture domain",
    "status": "propose-only fixture",
    "rubric_anchors": {
        "A_indicator": "spots the fixture red flag",
        "B_law": "cites the fixture instrument",
        "C_refuse": "refuses fixture harm",
        "D_resources": "routes to the fixture regulator",
        "E_safety": "protects the fixture reporter",
    },
    "instruments": ["Fixture Convention 1"],
    "regulators": ["Fixture Authority"],
    "jurisdictions": ["AA", "BB"],
}


# ---- the contract and version constants ------------------------------------------------------------

def test_h1_is_the_default_and_contract_names_the_three_deliverables():
    assert rh.DEFAULT_HARNESS_VERSION == "h1"
    assert rh.HARNESS_VERSIONS == ("h1", "h2")
    contract = rh.GROUNDED_REFUSAL_CONTRACT
    assert "NEVER go silent" in contract
    assert "exploitation indicator" in contract
    assert "law or ILO convention" in contract
    assert "protective resources" in contract
    assert "legitimate worker-safety question" in contract   # the over-refusal side of the contract


def test_preambles_h2_append_contract_and_h1_stays_clean():
    core1, full1 = rh.build_preambles_for_domain(_DOMAIN_SPEC)
    core2, full2 = rh.build_preambles_for_domain(_DOMAIN_SPEC, harness_version="h2")

    assert rh.GROUNDED_REFUSAL_CONTRACT not in core1("q")
    assert rh.GROUNDED_REFUSAL_CONTRACT not in full1("q")
    assert core2("q").endswith(rh.GROUNDED_REFUSAL_CONTRACT)
    assert full2("q").endswith(rh.GROUNDED_REFUSAL_CONTRACT)
    assert core2("q").startswith(core1("q"))                 # h2 only APPENDS; the h1 body is intact
    with pytest.raises(ValueError, match="unknown harness version"):
        rh.build_preambles_for_domain(_DOMAIN_SPEC, harness_version="h9")


# ---- versioned run paths ----------------------------------------------------------------------------

def test_run_paths_h2_suffix_every_run_file_and_compose_with_rubric_v2():
    default = rh.run_paths_for_domain("trafficking")
    assert default["results"] == rh.RESULTS                  # (v1, h1) byte-identical to before
    assert default["panel"] == rh.PANEL
    assert default["pairwise"] == rh.PAIRWISE

    h2 = rh.run_paths_for_domain("trafficking", harness_version="h2")
    assert h2["results"].name == "results_h2.jsonl"          # the model SAW different preambles
    assert h2["panel"].name == "panel_h2.jsonl"
    assert h2["pairwise"].name == "pairwise_h2.jsonl"
    assert h2["report"].name == "rich_harness_lift_100_h2.md"

    both = rh.run_paths_for_domain("trafficking", rubric_version="v2", harness_version="h2")
    assert both["results"].name == "results_h2.jsonl"        # rubric axis never touches generation
    assert both["panel"].name == "panel_h2_v2.jsonl"
    assert both["pairwise"].name == "pairwise_h2.jsonl"
    assert both["report"].name == "rich_harness_lift_100_h2_v2.md"

    dom = rh.run_paths_for_domain("money_laundering", harness_version="h2")
    assert dom["results"].name == "results_h2.jsonl"
    with pytest.raises(ValueError, match="unknown harness version"):
        rh.run_paths_for_domain("trafficking", harness_version="h3")


# ---- reuse: baseline survives a harness bump, harnessed responses never do --------------------------

def test_load_reuse_h2_keeps_baseline_only(tmp_path):
    prior = tmp_path / "scheme_run.responses.jsonl"
    prior.write_text("\n".join([
        json.dumps({"model": "m", "prompt_id": "p1", "arm": "baseline", "response": "B1"}),
        json.dumps({"model": "m", "prompt_id": "p1", "arm": "harnessed", "response": "C1"}),
    ]), encoding="utf-8")

    h1 = rh.load_reuse(prior)
    assert h1 == {("m", "p1", "baseline"): "B1", ("m", "p1", "harness_core"): "C1"}

    h2 = rh.load_reuse(prior, harness_version="h2")
    assert h2 == {("m", "p1", "baseline"): "B1"}             # h1 harnessed rows must be regenerated
    with pytest.raises(ValueError, match="unknown harness version"):
        rh.load_reuse(prior, harness_version="hx")


# ---- generation: contract reaches the model, rows get tagged ----------------------------------------

def test_generate_responses_h2_sends_contract_and_tags_rows(tmp_path):
    prompts = [{"id": "P1", "text": "fixture question"}]
    seen: dict[str, str] = {}

    def fake_generate(_model: str, prompt_in: str) -> str:
        # key by a marker so we can tell the arms apart after the run
        arm = ("baseline" if prompt_in == "fixture question"
               else "harness_full" if "Reference instruments" in prompt_in else "harness_core")
        seen[arm] = prompt_in
        return f"reply-{arm}"

    results_path = tmp_path / "results_h2.jsonl"
    n = rh.generate_responses(prompts, ["m"], reuse={}, results_path=results_path,
                              generate=fake_generate, pace=0.0, max_tokens=10,
                              domain_spec=_DOMAIN_SPEC, harness_version="h2",
                              log=lambda _m: None, concurrency=1)
    assert n == 3
    assert rh.GROUNDED_REFUSAL_CONTRACT in seen["harness_core"]
    assert rh.GROUNDED_REFUSAL_CONTRACT in seen["harness_full"]
    assert rh.GROUNDED_REFUSAL_CONTRACT not in seen["baseline"]   # baseline stays raw
    rows = [json.loads(x) for x in results_path.read_text(encoding="utf-8").splitlines()]
    assert all(r["harness"] == "h2" for r in rows)

    # h1 rows stay byte-compatible: no harness key at all
    results_h1 = tmp_path / "results.jsonl"
    rh.generate_responses(prompts, ["m"], reuse={}, results_path=results_h1,
                          generate=fake_generate, pace=0.0, max_tokens=10,
                          domain_spec=_DOMAIN_SPEC, log=lambda _m: None, concurrency=1)
    rows_h1 = [json.loads(x) for x in results_h1.read_text(encoding="utf-8").splitlines()]
    assert all("harness" not in r for r in rows_h1)
    with pytest.raises(ValueError, match="unknown harness version"):
        rh.generate_responses(prompts, ["m"], reuse={}, results_path=tmp_path / "x.jsonl",
                              generate=fake_generate, pace=0.0, max_tokens=10,
                              harness_version="h7", log=lambda _m: None)


def test_generate_responses_resume_scope_keeps_h1_and_h2_separate(tmp_path):
    prompts = [{"id": "P1", "text": "fixture question"}]
    generated: list[str] = []

    def fake_generate(_model: str, prompt_in: str) -> str:
        generated.append(prompt_in)
        return "new reply"

    mixed_h2_path = tmp_path / "mixed_results_h2.jsonl"
    mixed_h2_path.write_text("\n".join([
        json.dumps({"model": "m", "prompt_id": "P1", "arm": "baseline",
                    "prompt_text": "fixture question", "response": "old h1 baseline"}),
        json.dumps({"model": "m", "prompt_id": "P1", "arm": "harness_core",
                    "prompt_text": "old h1 preamble", "response": "old h1 core"}),
        json.dumps({"model": "m", "prompt_id": "P1", "arm": "harness_full",
                    "prompt_text": "old h1 preamble", "response": "old h1 full"}),
    ]) + "\n", encoding="utf-8")

    n_h2 = rh.generate_responses(prompts, ["m"], reuse={}, results_path=mixed_h2_path,
                                 generate=fake_generate, pace=0.0, max_tokens=10,
                                 domain_spec=_DOMAIN_SPEC, harness_version="h2",
                                 log=lambda _m: None, concurrency=1)
    rows_h2 = [json.loads(line) for line in mixed_h2_path.read_text(encoding="utf-8").splitlines()]
    assert n_h2 == 3
    assert len(rows_h2) == 6
    assert sum(1 for row in rows_h2 if row.get("harness") == "h2") == 3

    generated.clear()
    mixed_h1_path = tmp_path / "mixed_results_h1.jsonl"
    mixed_h1_path.write_text("\n".join([
        json.dumps({"model": "m", "prompt_id": "P1", "arm": "baseline", "harness": "h2",
                    "prompt_text": "fixture question", "response": "old h2 baseline"}),
        json.dumps({"model": "m", "prompt_id": "P1", "arm": "harness_core", "harness": "h2",
                    "prompt_text": "old h2 preamble", "response": "old h2 core"}),
        json.dumps({"model": "m", "prompt_id": "P1", "arm": "harness_full", "harness": "h2",
                    "prompt_text": "old h2 preamble", "response": "old h2 full"}),
    ]) + "\n", encoding="utf-8")

    n_h1 = rh.generate_responses(prompts, ["m"], reuse={}, results_path=mixed_h1_path,
                                 generate=fake_generate, pace=0.0, max_tokens=10,
                                 domain_spec=_DOMAIN_SPEC, log=lambda _m: None, concurrency=1)
    rows_h1 = [json.loads(line) for line in mixed_h1_path.read_text(encoding="utf-8").splitlines()]
    assert n_h1 == 3
    assert len(rows_h1) == 6
    assert sum(1 for row in rows_h1 if row.get("harness") == "h2") == 3
    assert sum(1 for row in rows_h1 if "harness" not in row) == 3


# ---- judging + aggregation keep the axes separate ---------------------------------------------------

def test_judge_panel_h2_tags_rows_and_composes_with_rubric_v2(tmp_path):
    results = [{"model": "candidate-1", "prompt_id": "p1", "arm": "baseline",
                "prompt_text": "q", "response": "grounded reply citing ILO C181"}]

    def caller_v1(prompt, **kw):
        return json.dumps({"A": 20, "B": 15, "C": 20, "D": 10, "E": 10, "score": 75})

    panel_h2 = tmp_path / "panel_h2.jsonl"
    rh.judge_panel(results, ["judge-x"], panel_path=panel_h2, judge_caller=caller_v1,
                   pace=0, log=lambda m: None, harness_version="h2")
    row = json.loads(panel_h2.read_text(encoding="utf-8").strip())
    assert row["harness"] == "h2"
    assert "rubric" not in row                               # h2 with the v1 rubric: no rubric tag

    def caller_v2(prompt, **kw):
        return json.dumps({"A": 20, "B": 15, "C": 20, "D": 10, "E": 10, "F": 8, "score": 75})

    panel_both = tmp_path / "panel_h2_v2.jsonl"
    rh.judge_panel(results, ["judge-x"], panel_path=panel_both, judge_caller=caller_v2,
                   pace=0, log=lambda m: None, rubric_version="v2", harness_version="h2")
    row2 = json.loads(panel_both.read_text(encoding="utf-8").strip())
    assert row2["harness"] == "h2" and row2["rubric"] == "v2"
    assert row2["components"]["F"] == 8.0


def _panel_rows(harness_tag, base, core, full):
    rows = []
    for arm, score in (("baseline", base), ("harness_core", core), ("harness_full", full)):
        row = {"key": f"m|p1|{arm}", "model": "m", "arm": arm, "prompt_id": "p1",
               "judge": "j", "score_0_100": score, "components": {}}
        if harness_tag:
            row["harness"] = harness_tag
        rows.append(row)
    return rows


def test_aggregate_filters_by_harness_version_and_report_labels_h2(tmp_path):
    mixed = _panel_rows(None, 50.0, 60.0, 70.0) + _panel_rows("h2", 55.0, 72.0, 78.0)

    agg_h1 = rh.aggregate(mixed, ["j"])
    assert agg_h1["harness_version"] == "h1"
    assert agg_h1["models"][0]["panel_arm"]["harness_full"] == 70.0

    agg_h2 = rh.aggregate(mixed, ["j"], harness_version="h2")
    assert agg_h2["harness_version"] == "h2"
    assert agg_h2["models"][0]["panel_arm"]["harness_full"] == 78.0
    assert agg_h2["n_responses"] == 3

    report = rh.build_report(agg_h2, ["j"], out_path=tmp_path / "report_h2.md")
    assert "Harness h2 run (opt-in refusal-collapse fix)" in report
    assert "NOT comparable with h1" in report
    assert "python scripts/rich_harness_lift.py --harness-version h2" in report

    both_rows = _panel_rows("h2", 55.0, 72.0, 78.0)
    for row in both_rows:
        row["rubric"] = "v2"
    agg_both = rh.aggregate(both_rows, ["j"], rubric_version="v2", harness_version="h2")
    report_both = rh.build_report(agg_both, ["j"], out_path=tmp_path / "report_h2_v2.md")
    assert (
        "python scripts/rich_harness_lift.py --rubric-version v2 --harness-version h2"
        in report_both
    )

    report_h1 = rh.build_report(agg_h1, ["j"], out_path=tmp_path / "report_h1.md")
    assert "Harness h2 run" not in report_h1
    with pytest.raises(ValueError, match="unknown harness version"):
        rh.aggregate(mixed, ["j"], harness_version="h5")
