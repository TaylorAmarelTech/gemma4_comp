"""Tests for scripts/multi_judge.py -- the multi-judge agreement panel.

Offline: the judge model call is injected, so no network / API key is needed.
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


mj = _load("multi_judge", _ROOT / "scripts" / "multi_judge.py")


def test_judge_one_parses_and_clamps():
    assert mj.judge_one("p", "r", model="m", caller=lambda p, **k: '{"score": 7}') == 7.0
    assert mj.judge_one("p", "r", model="m", caller=lambda p, **k: '{"score": 15}') == 10.0
    assert mj.judge_one("p", "r", model="m", caller=lambda p, **k: "garbage") == 0.0


def _panel():
    # model A, prompt p1: baseline 3/4, harnessed 8/9 by two judges -> lift 5 each, spread 0
    return [
        {"key": "A|p1|baseline", "model": "A", "arm": "baseline", "prompt_id": "p1", "judge": "j1", "score": 3},
        {"key": "A|p1|harnessed", "model": "A", "arm": "harnessed", "prompt_id": "p1", "judge": "j1", "score": 8},
        {"key": "A|p1|baseline", "model": "A", "arm": "baseline", "prompt_id": "p1", "judge": "j2", "score": 4},
        {"key": "A|p1|harnessed", "model": "A", "arm": "harnessed", "prompt_id": "p1", "judge": "j2", "score": 9},
    ]


def test_aggregate_computes_per_judge_lift_and_agreement():
    agg = mj.aggregate(_panel(), ["j1", "j2"])
    r = agg["rows"][0]
    assert r["model"] == "A"
    assert r["judge_lifts"]["j1"] == 5.0 and r["judge_lifts"]["j2"] == 5.0
    assert r["panel_lift"] == 5.0 and r["judge_spread"] == 0.0   # judges fully agree on the lift
    assert agg["n_responses"] == 2                                # one baseline + one harnessed key


def test_build_report_states_robustness(tmp_path):
    md = mj.build_report(mj.aggregate(_panel(), ["j1", "j2"]), ["j1", "j2"], out_path=tmp_path / "r.md")
    assert "robust to the choice of judge" in md.lower()
    assert "`j1`" in md and "Judge spread" in md


def test_krippendorff_alpha_interval():
    # perfect agreement: every item rated identically -> alpha = 1
    perfect = {"i1": [8, 8], "i2": [3, 3], "i3": [6, 6], "i4": [9, 9]}
    assert mj.krippendorff_alpha(perfect) == 1.0
    # systematic disagreement: judges flip on every item -> alpha negative
    disagree = {"i1": [10, 0], "i2": [0, 10], "i3": [10, 0], "i4": [0, 10]}
    a = mj.krippendorff_alpha(disagree)
    assert a is not None and a < 0
    # single-rating items contribute nothing
    assert mj.krippendorff_alpha({"i1": [5]}) is None


def test_aggregate_reports_alpha():
    agg = mj.aggregate(_panel(), ["j1", "j2"])
    assert "krippendorff_alpha" in agg and agg["krippendorff_alpha"] >= 0.8   # the two judges agree


def test_run_panel_resumable_offline(tmp_path, monkeypatch):
    monkeypatch.setattr(mj, "PANEL_CKPT", tmp_path / "p.jsonl")
    results = [{"model": "A", "prompt_id": "p1", "arm": "baseline", "prompt_text": "q", "response": "a"},
               {"model": "A", "prompt_id": "p1", "arm": "harnessed", "prompt_text": "q", "response": "b"}]
    panel = mj.run_panel(results, ["j1"], caller=lambda p, **k: '{"score": 6}')
    assert len(panel) == 2 and all(p["judge"] == "j1" for p in panel)
    # re-run is a no-op (already done -> resumable)
    assert len(mj.run_panel(results, ["j1"], caller=lambda p, **k: '{"score": 9}')) == 2
    assert {p["score"] for p in mj.load_results(tmp_path / "p.jsonl")} == {6.0}   # not re-judged


def test_model_family_groups_variants():
    assert mj.model_family("glm-5.2") == "glm"
    assert mj.model_family("qwen3.5:397b") == mj.model_family("qwen3-coder:480b") == "qwen"
    assert mj.model_family("gpt-oss:120b") == "gpt-oss"          # gpt-oss is its own family
    assert mj.model_family("kimi-k2.7-code") == "kimi"


def test_run_panel_excludes_self_family(tmp_path, monkeypatch):
    monkeypatch.setattr(mj, "PANEL_CKPT", tmp_path / "p.jsonl")
    # a glm candidate must NOT be scored by the glm judge, but IS scored by gpt-oss + qwen
    results = [{"model": "glm-5.2", "prompt_id": "p1", "arm": "baseline", "prompt_text": "q", "response": "a"}]
    panel = mj.run_panel(results, ["glm-5.2", "gpt-oss:120b", "qwen3.5:397b"],
                         caller=lambda p, **k: '{"score": 7}')
    judges = {p["judge"] for p in panel}
    assert "glm-5.2" not in judges                                # never grades its own family
    assert judges == {"gpt-oss:120b", "qwen3.5:397b"}
    # opting out restores the naive behaviour
    monkeypatch.setattr(mj, "PANEL_CKPT", tmp_path / "p2.jsonl")
    panel2 = mj.run_panel(results, ["glm-5.2"], caller=lambda p, **k: '{"score": 7}',
                          exclude_self_family=False)
    assert len(panel2) == 1 and panel2[0]["judge"] == "glm-5.2"
