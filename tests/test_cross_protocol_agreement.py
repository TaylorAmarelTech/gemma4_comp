"""Cross-protocol agreement: the batched and per-dimension judge protocols are compared on the
prompts BOTH graded, so the headline lift can be checked for elicitation artifacts offline."""
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


x = _load("cross_protocol_agreement", _ROOT / "scripts" / "cross_protocol_agreement.py")


def _row(pid, arm, score, judge="j1", model="gemma4:31b"):
    return {"model": model, "prompt_id": pid, "arm": arm, "judge": judge, "score_0_100": score}


def _panel(tmp_path, name, rows):
    p = tmp_path / name
    p.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return p


def test_arm_means_average_over_judges(tmp_path):
    panel = _panel(tmp_path, "p.jsonl", [
        _row("p1", "baseline", 40, judge="j1"), _row("p1", "baseline", 60, judge="j2"),
        _row("p1", "harness_core", 90, judge="j1"),
    ])
    arms = x.load_arm_means(panel, "gemma4:31b")
    assert arms["p1"]["baseline"] == 50.0          # (40+60)/2
    assert arms["p1"]["harness_core"] == 90.0


def test_other_models_and_unpaired_prompts_are_excluded(tmp_path):
    panel = _panel(tmp_path, "p.jsonl", [
        _row("p1", "baseline", 40), _row("p1", "harness_core", 90),
        _row("p2", "baseline", 10),                                   # no core arm -> unpaired
        _row("p3", "baseline", 10, model="other:7b"), _row("p3", "harness_core", 99, model="other:7b"),
    ])
    lifts = x.paired_lifts(x.load_arm_means(panel, "gemma4:31b"))
    assert lifts == {"p1": 50.0}


def test_compare_restricts_to_shared_prompts_and_reports_the_delta():
    batched = {"p1": 50.0, "p2": 30.0, "p3": 10.0}   # p3 is batched-only
    perdim = {"p1": 40.0, "p2": 30.0, "p4": 99.0}    # p4 is perdim-only
    c = x.compare(batched, perdim)
    assert c["n_shared"] == 2                        # p1, p2
    assert c["n_batched_paired"] == 3 and c["n_perdim_paired"] == 3
    assert c["batched_lift"] == 40.0 and c["perdim_lift"] == 35.0
    assert c["protocol_delta"] == 5.0                # ((50-40)+(30-30))/2
    assert c["sign_agreement"] == 100.0              # both positive on both shared prompts


def test_hurt_sets_separate_robust_regressions_from_grading_sensitivity():
    batched = {"p1": -5.0, "p2": -3.0, "p3": 20.0}
    perdim = {"p1": -4.0, "p2": 2.0, "p3": -1.0}
    c = x.compare(batched, perdim)
    assert c["batched_hurts"] == 2 and c["perdim_hurts"] == 2
    assert c["hurts_in_both"] == 1                   # only p1 is a hurt under both protocols
    assert c["hurts_in_either"] == 3
    assert c["sign_agreement"] == round(100 * 1 / 3, 1)  # only p1 agrees on sign


def test_render_calls_a_sub_five_percent_gap_not_an_artifact():
    # +0.4 on a +40 lift is statistically detectable at scale but 1% of the effect.
    c = x.compare({f"p{i}": 40.4 for i in range(200)}, {f"p{i}": 40.0 for i in range(200)})
    out = x.render(c, model="gemma4:31b", today="2026-07-25",
                   batched_path=x.BATCHED, perdim_path=x.PERDIM)
    assert "not** an artifact of the batched grading prompt" in out
    assert "% of the" in out                         # relative size is always shown


def test_render_flags_a_material_gap_as_protocol_dependent():
    c = x.compare({f"p{i}": 40.0 for i in range(200)}, {f"p{i}": 20.0 for i in range(200)})
    out = x.render(c, model="gemma4:31b", today="2026-07-25",
                   batched_path=x.BATCHED, perdim_path=x.PERDIM)
    assert "protocol-dependent" in out


def test_render_handles_no_shared_prompts_without_claiming_a_result():
    c = x.compare({"p1": 5.0}, {"p2": 5.0})
    out = x.render(c, model="gemma4:31b", today="2026-07-25",
                   batched_path=x.BATCHED, perdim_path=x.PERDIM)
    assert "nothing to compare" in out
    assert "Protocol delta" not in out


def test_panel_label_never_leaks_an_out_of_repo_absolute_path():
    label = x._label(Path("C:/Users/someone/AppData/Local/Temp/panel.jsonl").resolve())
    assert label == "panel.jsonl"
    assert "Users" not in label and "AppData" not in label


def test_missing_panel_yields_no_rows_rather_than_raising(tmp_path):
    assert x.load_arm_means(tmp_path / "absent.jsonl", "gemma4:31b") == {}
