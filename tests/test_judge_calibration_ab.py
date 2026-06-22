"""Tests for scripts/judge_calibration_ab.py -- calibrated-vs-default judge distribution A/B."""
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


ab = _load("judge_calibration_ab", _ROOT / "scripts" / "judge_calibration_ab.py")


def test_clustering_metrics_flags_ceiling_pileup():
    clustered = [10.0] * 8 + [9.0] * 2                 # all at the ceiling, integer
    m = ab.clustering_metrics(clustered)
    assert m["distinct_values"] == 2 and m["pct_ceiling_ge9"] == 100.0 and m["pct_integer"] == 100.0
    spread = [4.3, 5.1, 6.8, 7.2, 7.9, 8.3, 8.6, 9.1, 3.5, 6.0]   # fine-grained, mostly non-ceiling
    s = ab.clustering_metrics(spread)
    assert s["distinct_values"] > m["distinct_values"]            # more resolution
    assert s["pct_ceiling_ge9"] < m["pct_ceiling_ge9"]            # less pile-up
    assert s["entropy_bits"] > m["entropy_bits"]                  # more spread
    assert s["pct_integer"] == 0.0                               # all decimals


def test_run_ab_scores_both_arms_and_resumes(tmp_path):
    items = [{"key": "m|p1|baseline", "prompt_text": "q1", "response": "r1"},
             {"key": "m|p1|harnessed", "prompt_text": "q1", "response": "r2"}]
    calls = {"n": 0}

    def judge(prompt, response, *, model, calibrated):
        calls["n"] += 1
        return 8.3 if calibrated else 9.0           # calibrated finer, default round

    ck = tmp_path / "ab.jsonl"
    rows = ab.run_ab(items, judge_model="j", judge=judge, ckpt=ck, pace=0)
    assert len(rows) == 4 and calls["n"] == 4       # 2 items x 2 arms
    assert {r["arm"] for r in rows} == {"default", "calibrated"}
    ab.run_ab(items, judge_model="j", judge=judge, ckpt=ck, pace=0)   # resume
    assert calls["n"] == 4                          # nothing re-judged


def test_aggregate_and_report(tmp_path):
    rows = []
    for i in range(6):
        rows.append({"key": f"k{i}", "arm": "default", "score": 9.0 if i % 2 else 10.0})
        rows.append({"key": f"k{i}", "arm": "calibrated", "score": 7.0 + i * 0.3})
    agg = ab.aggregate(rows)
    assert agg["default"]["distinct_values"] == 2          # only 9 and 10
    assert agg["calibrated"]["distinct_values"] == 6       # spread out
    md = ab.build_report(agg, judge_model="gpt-oss:120b", out_path=tmp_path / "r.md")
    assert "de-cluster" in md and "distinct values" in md
    assert "spreads the scores out" in md                  # verdict: calibrated wins here
