"""Tests for scripts/negative_control.py -- the length-matched placebo arm."""
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


nc = _load("negative_control", _ROOT / "scripts" / "negative_control.py")


def test_placebo_is_length_matched_and_knowledge_free():
    p = nc.build_placebo_preamble(600)
    assert len(p) >= 600                       # padded up to the target
    assert len(p) < 600 + 120                  # but not wildly past it (<= one sentence over)
    low = p.lower()
    # the whole point: it carries NO domain knowledge the real preamble would
    for banned in ("ilo", "fee", "bondage", "passport", "convention", "statute", "indicator"):
        assert banned not in low


def test_run_placebo_writes_cells_and_resumes(tmp_path):
    prompts = [{"id": "P1", "text": "is this normal?"}, {"id": "P2", "text": "help me hire"}]
    models = ["m1"]
    calls = {"n": 0}

    def generate(model, prompt_in):
        calls["n"] += 1
        assert "GENERAL GUIDANCE" in prompt_in          # the placebo preamble was prepended
        assert "SAFETY GROUNDING" not in prompt_in       # NOT the real harness preamble
        return "a long, careful, responsible answer that addresses the situation in detail."

    def grade(text, response):
        return [("dim_a", 7.0), ("dim_b", 6.0)]

    ck = tmp_path / "nc.jsonl"
    n = nc.run_placebo(prompts, models, real_preamble=lambda t: "x" * 400,
                       generate=generate, grade=grade, ckpt=ck, pace=0)
    assert n == 4 and calls["n"] == 2                    # 2 prompts x 1 model, 2 dims each
    cells = nc.load_cells(ck)
    assert {c["arm"] for c in cells} == {"placebo"}
    # resume: nothing new generated or graded
    n2 = nc.run_placebo(prompts, models, real_preamble=lambda t: "x" * 400,
                        generate=generate, grade=grade, ckpt=ck, pace=0)
    assert n2 == 0 and calls["n"] == 2


def test_three_way_contrasts_isolate_the_knowledge_effect():
    baseline = {("p1", "m"): 5.0, ("p2", "m"): 4.0}
    placebo = {("p1", "m"): 6.0, ("p2", "m"): 5.0}     # +1 over baseline (any-preamble effect)
    harnessed = {("p1", "m"): 8.0, ("p2", "m"): 7.0}   # +2 over placebo (knowledge effect)
    s = nc.three_way(baseline, placebo, harnessed, ["m"])
    ov = s["overall"]
    assert ov["n"] == 2
    assert ov["mean_baseline"] == 4.5 and ov["mean_placebo"] == 5.5 and ov["mean_harnessed"] == 7.5
    assert ov["placebo_minus_baseline"]["mean"] == 1.0
    assert ov["harnessed_minus_placebo"]["mean"] == 2.0     # the headline contrast
    assert ov["harnessed_minus_baseline"]["mean"] == 3.0


def test_build_report_renders(tmp_path):
    baseline = {("p1", "m"): 5.0, ("p2", "m"): 4.0}
    placebo = {("p1", "m"): 6.0, ("p2", "m"): 5.0}
    harnessed = {("p1", "m"): 8.0, ("p2", "m"): 7.0}
    s = nc.three_way(baseline, placebo, harnessed, ["m"])
    md = nc.build_report(s, lengths={"real_mean": 400.0, "placebo_mean": 410.0},
                         out_path=tmp_path / "r.md")
    assert "Negative control" in md and "harnessed − placebo" in md
    assert "KNOWLEDGE effect" in md
