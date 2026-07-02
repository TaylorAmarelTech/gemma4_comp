"""Tests for scripts/pairwise_lift.py -- head-to-head pairwise harness lift."""
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


pl = _load("pairwise_lift", _ROOT / "scripts" / "pairwise_lift.py")


def test_load_pairs_keeps_only_complete(tmp_path):
    rp = tmp_path / "resp.jsonl"
    rows = [{"prompt_id": "p1", "arm": "baseline", "response": "b1", "prompt_text": "q1"},
            {"prompt_id": "p1", "arm": "harnessed", "response": "h1", "prompt_text": "q1"},
            {"prompt_id": "p2", "arm": "baseline", "response": "b2", "prompt_text": "q2"},  # no harnessed
            {"prompt_id": {"private": "worker@example.com"}, "arm": "baseline",
             "response": "structured prompt id", "prompt_text": "q3"},
            {"prompt_id": "p3", "arm": ["baseline"], "response": "structured arm", "prompt_text": "q3"},
            {"prompt_id": "p3", "arm": "baseline",
             "response": {"private": "worker@example.com"}, "prompt_text": "q3"},
            {"prompt_id": "p4", "arm": "baseline", "response": "b4", "prompt_text": ["q4"]},
            {"prompt_id": "p4", "arm": "harnessed", "response": "h4", "prompt_text": ["q4"]}]
    rp.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    pairs = pl.load_pairs(rp)
    assert len(pairs) == 1 and pairs[0]["prompt_id"] == "p1"
    assert pairs[0]["baseline"] == "b1" and pairs[0]["harnessed"] == "h1"


def test_run_pairwise_resumes(tmp_path):
    pairs = [{"prompt_id": "p1", "prompt_text": "q", "baseline": "b", "harnessed": "h"},
             {"prompt_id": "p2", "prompt_text": "q", "baseline": "b", "harnessed": "h"}]
    calls = {"n": 0}

    def judge(prompt, a, b, *, model):
        calls["n"] += 1
        return 4.0
    ck = tmp_path / "pw.jsonl"
    rows = pl.run_pairwise(pairs, judge_model="j", judge=judge, ckpt=ck, pace=0)
    assert len(rows) == 2 and calls["n"] == 2
    pl.run_pairwise(pairs, judge_model="j", judge=judge, ckpt=ck, pace=0)   # resume
    assert calls["n"] == 2                                                  # nothing re-judged


def test_run_pairwise_skips_malformed_pairs_and_checkpoint_rows(tmp_path):
    pairs = [
        {"prompt_id": "p1", "prompt_text": "q", "baseline": "b", "harnessed": "h"},
        {"prompt_id": {"private": "worker@example.com"}, "prompt_text": "q", "baseline": "b", "harnessed": "h"},
        {"prompt_id": "p2", "prompt_text": ["q"], "baseline": "b", "harnessed": "h"},
    ]
    ck = tmp_path / "pw.jsonl"
    ck.write_text(
        "\n".join([
            json.dumps({"prompt_id": ["p-bad"], "pairwise_lift": 4.0}),
            json.dumps({"prompt_id": "p-old", "pairwise_lift": "nan"}),
            "{not-json",
        ]) + "\n",
        encoding="utf-8",
    )
    calls = {"n": 0}

    def judge(prompt, a, b, *, model):
        calls["n"] += 1
        return 4.0

    rows = pl.run_pairwise(pairs, judge_model="j", judge=judge, ckpt=ck, pace=0)

    assert calls["n"] == 1
    assert rows == [{"prompt_id": "p1", "pairwise_lift": 4.0}]


def test_aggregate_win_rate_and_spread():
    rows = [{"prompt_id": f"p{i}", "pairwise_lift": v}
            for i, v in enumerate([5.0, 3.0, 6.5, -1.0, 0.0, 4.0, 2.5, 7.0])]
    rows.extend([
        {"prompt_id": "bad", "pairwise_lift": "nan"},
        {"prompt_id": "bad2", "pairwise_lift": {"private": "worker@example.com"}},
    ])
    agg = pl.aggregate(rows)
    assert agg["n"] == 8
    assert agg["win_pct"] == 75.0          # 6 of 8 are > 0.5
    assert agg["loss_pct"] == 12.5         # 1 of 8 < -0.5
    assert agg["distinct_values"] >= 7     # spreads across the range (not clustered)


def test_build_report_renders(tmp_path):
    rows = [{"prompt_id": f"p{i}", "pairwise_lift": 4.0 + i * 0.2} for i in range(6)]
    md = pl.build_report(pl.aggregate(rows), judge_model="gpt-oss:120b", out_path=tmp_path / "r.md")
    assert "Pairwise harness lift" in md and "head-to-head" in md and "win" in md.lower()
