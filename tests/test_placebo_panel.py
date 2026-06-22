"""Tests for scripts/placebo_panel.py -- placebo control under a diverse judge panel."""
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


pp = _load("placebo_panel", _ROOT / "scripts" / "placebo_panel.py")


def _arms():
    return {("gemma4:31b", "p1"): {"prompt_text": "q1", "baseline": "b1", "placebo": "pl1", "harnessed": "h1"},
            ("gemma4:31b", "p2"): {"prompt_text": "q2", "baseline": "b2", "placebo": "pl2", "harnessed": "h2"}}


def test_run_panel_judges_every_judge_x_arm_and_resumes(tmp_path):
    calls = {"n": 0}

    def judge(prompt, response, *, model):
        calls["n"] += 1
        return {"b": 4.0, "p": 5.0, "h": 8.0}[response[0]]

    ck = tmp_path / "panel.jsonl"
    rows = pp.run_panel(_arms(), judges=["jA", "jB"], judge=judge, ckpt=ck, pace=0,
                        exclude_self_family=False)
    # 2 judges x 2 prompts x 3 arms
    assert len(rows) == 12 and calls["n"] == 12
    assert {r["judge"] for r in rows} == {"jA", "jB"}
    # resume: nothing new
    rows2 = pp.run_panel(_arms(), judges=["jA", "jB"], judge=judge, ckpt=ck, pace=0,
                         exclude_self_family=False)
    assert len(rows2) == 12 and calls["n"] == 12


def test_self_family_exclusion_skips_own_family(tmp_path):
    seen = {"judges": set()}

    def judge(prompt, response, *, model):
        seen["judges"].add(model)
        return 7.0

    # candidate is gemma4:31b; a "gemma4:..." judge must be excluded, gpt-oss must run
    arms = {("gemma4:31b", "p1"): {"prompt_text": "q", "baseline": "b", "placebo": "p", "harnessed": "h"}}
    pp.run_panel(arms, judges=["gemma4:31b", "gpt-oss:120b"], judge=judge, ckpt=tmp_path / "c.jsonl",
                 pace=0, exclude_self_family=True)
    assert "gpt-oss:120b" in seen["judges"]
    assert "gemma4:31b" not in seen["judges"]      # never judged its own family


def test_aggregate_per_judge_and_panel_summary():
    rows = []
    for jm, hval in (("jA", 8.0), ("jB", 9.0)):       # both judges: harnessed > placebo
        for pid in ("p1", "p2", "p3"):
            rows += [{"judge": jm, "model": "m", "prompt_id": pid, "arm": "baseline", "score": 4.0},
                     {"judge": jm, "model": "m", "prompt_id": pid, "arm": "placebo", "score": 5.0},
                     {"judge": jm, "model": "m", "prompt_id": pid, "arm": "harnessed", "score": hval}]
    agg = pp.aggregate(rows)
    assert set(agg["per_judge"]) == {"jA", "jB"}
    assert agg["per_judge"]["jA"]["harnessed_minus_placebo"]["mean"] == 3.0   # 8 - 5
    assert agg["per_judge"]["jB"]["harnessed_minus_placebo"]["mean"] == 4.0   # 9 - 5
    panel = agg["panel"]
    assert panel["n_judges"] == 2 and panel["all_positive"] is True
    assert panel["min_hp"] == 3.0 and panel["max_hp"] == 4.0
    assert panel["panel_mean_harnessed_minus_placebo"] == 3.5


def test_seed_from_single_is_idempotent(tmp_path):
    single = tmp_path / "single.jsonl"
    single.write_text("\n".join(json.dumps(
        {"model": "gemma4:31b", "prompt_id": f"p{i}", "arm": a, "score": 5.0 + i})
        for i in range(2) for a in ("baseline", "placebo", "harnessed")) + "\n", encoding="utf-8")
    panel = tmp_path / "panel.jsonl"
    n1 = pp.seed_from_single(panel, single)
    n2 = pp.seed_from_single(panel, single)   # second call must add nothing
    assert n1 == 6 and n2 == 0
    rows = [json.loads(x) for x in panel.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert all(r["judge"] == "gpt-oss:120b" for r in rows) and len(rows) == 6


def test_build_report_renders(tmp_path):
    rows = []
    for jm in ("jA", "jB"):
        for pid in ("p1", "p2", "p3", "p4"):
            rows += [{"judge": jm, "model": "m", "prompt_id": pid, "arm": "baseline", "score": 4.0},
                     {"judge": jm, "model": "m", "prompt_id": pid, "arm": "placebo", "score": 5.0},
                     {"judge": jm, "model": "m", "prompt_id": pid, "arm": "harnessed", "score": 8.0}]
    md = pp.build_report(pp.aggregate(rows), out_path=tmp_path / "r.md")
    assert "diverse judge panel" in md and "harnessed − placebo" in md and "self-family exclusion" in md.lower()
