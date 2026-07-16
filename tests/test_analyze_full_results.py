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
    assert agg["paired_prompt_ids"] == 2
    assert agg["fully_paired_prompt_ids"] == 1
    assert m["n_full_pair"] == 1 and m["n_core_full_pair"] == 1
    assert m["core_better"] == 1 and m["full_better"] == 0


def test_aggregate_skips_unpaired_and_nonnumeric():
    rows = [_row("q1", "baseline", 30), _row("q1", "harness_core", "N/A"),   # non-numeric score dropped
            {"model": "gemma4:31b", "prompt_id": "q2", "arm": "baseline"}]    # no score
    agg = a.aggregate(rows)
    # q1 core is non-numeric -> not paired; q2 has no score -> nothing paired
    assert agg["per_model"] == [] or all(r["n_pair"] == 0 for r in agg["per_model"])


def test_render_states_coverage_against_registry():
    rows = [_row("p1", "baseline", 40), _row("p1", "harness_core", 90)]
    out = a.render(a.aggregate(rows), registry=74640, today="2026-07-11")
    assert "coverage: 0 of the 74,640-prompt registry have all three arms" in out
    assert "1 have baseline/core pairs" in out
    assert "credit-gated" in out


def test_single_arm_rows_do_not_inflate_paired_coverage():
    rows = [
        _row("paired", "baseline", 40),
        _row("paired", "harness_core", 80),
        _row("partial", "harness_full", 90),
    ]
    agg = a.aggregate(rows)
    assert agg["graded_prompt_ids"] == 2
    assert agg["paired_prompt_ids"] == 1
    assert agg["fully_paired_prompt_ids"] == 0


def test_positive_full_minus_core_reports_full_as_winner():
    rows = [
        _row("p1", "baseline", 40),
        _row("p1", "harness_core", 80),
        _row("p1", "harness_full", 90),
    ]
    out = a.render(a.aggregate(rows), registry=100, today="2026-07-11")
    assert "full - core = +10" in out
    assert "full outperforms core on average; core >= full does not hold" in out
    assert "core scores higher on 0, full scores higher on 1" in out
    assert "core >= full holds" not in out


def test_component_lift_uses_only_prompt_pairs_with_both_component_scores():
    rows = [
        _row("p1", "baseline", 40, {"A": 5}),
        _row("p1", "harness_core", 80, {"A": 15}),
        _row("p2", "baseline", 50, {"A": 100}),
        _row("p2", "harness_core", 70),
    ]
    model = a.aggregate(rows)["per_model"][0]
    assert model["components"]["A"] == 10.0
    assert model["component_n"]["A"] == 1


def test_no_hurt_does_not_report_a_positive_delta_as_the_worst_hurt():
    rows = [_row("p1", "baseline", 40), _row("p1", "harness_core", 80)]
    agg = a.aggregate(rows)
    assert agg["per_model"][0]["hurt_worst"] is None
    out = a.render(agg, registry=100, today="2026-07-11")
    assert "HURTS on 0." in out
    assert "worst 40" not in out


def test_statistics_block_reports_ci_sign_test_and_win_rate():
    rows = []
    for i in range(10):
        rows += [_row(f"h{i}", "baseline", 40), _row(f"h{i}", "harness_core", 60)]
    for i in range(2):
        rows += [_row(f"x{i}", "baseline", 60), _row(f"x{i}", "harness_core", 50)]
    m = a.aggregate(rows)["per_model"][0]
    stats = m["statistics"]
    # exact two-sided sign test: 10 wins vs 2 losses over 12 informative pairs
    assert stats["sign_test_two_sided_p"] == round(2 * (1 + 12 + 66) / 4096, 6)
    assert stats["win_rate"] == round(10 / 12, 4)
    low, high = stats["win_rate_wilson_95"]
    assert 0 < low < 10 / 12 < high < 1
    lo, hi = stats["lift_bootstrap_95"]
    assert lo <= m["lift_core"] <= hi


def test_sign_test_normal_approximation_matches_direction_at_large_n():
    p_small = a._sign_test_two_sided_p(30, 10)
    p_large = a._sign_test_two_sided_p(3000, 1000)
    assert p_small is not None and p_large is not None
    assert p_large < p_small < 0.05
    assert a._sign_test_two_sided_p(0, 0) is None


def test_registry_breakdowns_group_by_category_and_corridor():
    rows = [
        _row("p1", "baseline", 40), _row("p1", "harness_core", 90),
        _row("p2", "baseline", 60), _row("p2", "harness_core", 55),
    ]
    meta = {
        "p1": {"category": "labor_trafficking", "corridor": "NP->MY", "difficulty": "hard"},
        "p2": {"category": "debt_bondage", "corridor": "PH->SA", "difficulty": "medium"},
    }
    m = a.aggregate(rows, registry_meta=meta)["per_model"][0]
    cats = {c["value"]: c for c in m["breakdowns"]["category"]}
    assert cats["labor_trafficking"]["n"] == 1 and cats["labor_trafficking"]["lift"] == 50.0
    assert cats["debt_bondage"]["lift"] == -5.0 and cats["debt_bondage"]["hurts"] == 1
    corridors = {c["value"]: c for c in m["breakdowns"]["corridor"]}
    assert corridors["NP->MY"]["helps"] == 1


def test_breakdowns_absent_without_registry_meta():
    rows = [_row("p1", "baseline", 40), _row("p1", "harness_core", 90)]
    m = a.aggregate(rows)["per_model"][0]
    assert m["breakdowns"] is None


def test_per_judge_lift_is_computed_independently():
    rows = [
        {**_row("p1", "baseline", 40), "judge": "j1"},
        {**_row("p1", "harness_core", 90), "judge": "j1"},
        {**_row("p1", "baseline", 60), "judge": "j2"},
        {**_row("p1", "harness_core", 65), "judge": "j2"},
    ]
    m = a.aggregate(rows)["per_model"][0]
    per_judge = {j["judge"]: j for j in m["per_judge"]}
    assert per_judge["j1"]["lift"] == 50.0 and per_judge["j1"]["n_pair"] == 1
    assert per_judge["j2"]["lift"] == 5.0


def test_render_includes_statistics_and_breakdown_sections():
    rows = [
        {**_row("p1", "baseline", 40), "judge": "j1"},
        {**_row("p1", "harness_core", 90), "judge": "j1"},
        {**_row("p2", "baseline", 60), "judge": "j1"},
        {**_row("p2", "harness_core", 55), "judge": "j1"},
    ]
    meta = {
        "p1": {"category": "labor_trafficking", "corridor": "NP->MY", "difficulty": "hard"},
        "p2": {"category": "debt_bondage", "corridor": "PH->SA", "difficulty": "medium"},
    }
    out = a.render(a.aggregate(rows, registry_meta=meta), registry=100, today="2026-07-11")
    assert "## Statistical strength" in out
    assert "## Per-judge robustness" in out
    assert "## Lift by prompt category" in out
    assert "labor_trafficking" in out
    assert "sign test" in out
