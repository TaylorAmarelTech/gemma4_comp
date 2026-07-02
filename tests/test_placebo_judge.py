"""Tests for scripts/placebo_judge.py -- placebo control on the LLM judge (3-arm)."""
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


pj = _load("placebo_judge", _ROOT / "scripts" / "placebo_judge.py")


def _arms():
    # two prompts, all 3 arms each
    return {("m", "p1"): {"prompt_text": "q1", "baseline": "b1", "placebo": "pl1", "harnessed": "h1"},
            ("m", "p2"): {"prompt_text": "q2", "baseline": "b2", "placebo": "pl2", "harnessed": "h2"}}


def test_load_arms_skips_malformed_response_rows(tmp_path, monkeypatch):
    perdim = tmp_path / "perdim.jsonl"
    placebo = tmp_path / "placebo.jsonl"
    perdim.write_text(
        "\n".join([
            json.dumps({"model": "m", "prompt_id": "p1", "arm": "baseline", "response": "b1"}),
            json.dumps({"model": "m", "prompt_id": "p1", "arm": "harnessed", "response": "h1"}),
            json.dumps({"model": {"private": "worker@example.com"}, "prompt_id": "p2",
                        "arm": "baseline", "response": "bad-model"}),
            json.dumps({"model": "m", "prompt_id": ["p2"], "arm": "harnessed", "response": "bad-pid"}),
            json.dumps({"model": "m", "prompt_id": "p2", "arm": ["baseline"], "response": "bad-arm"}),
            json.dumps({"model": "m", "prompt_id": "p2", "arm": "baseline",
                        "response": {"private": "worker@example.com"}}),
        ]) + "\n",
        encoding="utf-8",
    )
    placebo.write_text(
        json.dumps({"model": "m", "prompt_id": "p1", "arm": "placebo", "response": "pl1"}) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(pj, "_prompt_text_index", lambda: {"p1": "q1", "p2": "q2"})

    arms = pj.load_arms(perdim, placebo)

    assert arms == {
        ("m", "p1"): {
            "prompt_text": "q1",
            "baseline": "b1",
            "placebo": "pl1",
            "harnessed": "h1",
        }
    }


def test_run_judge_resumable_and_three_arms(tmp_path):
    calls = {"n": 0}

    def judge(prompt, response, *, model):
        calls["n"] += 1
        return {"b": 4.0, "p": 5.0, "h": 8.0}[response[0]]   # baseline 4, placebo 5, harnessed 8

    ck = tmp_path / "pj.jsonl"
    rows = pj.run_judge(_arms(), judge_model="j", judge=judge, ckpt=ck, pace=0)
    assert len(rows) == 6 and calls["n"] == 6              # 2 prompts x 3 arms
    # resume: nothing new judged
    rows2 = pj.run_judge(_arms(), judge_model="j", judge=judge, ckpt=ck, pace=0)
    assert len(rows2) == 6 and calls["n"] == 6


def test_run_judge_ignores_malformed_checkpoint_rows(tmp_path):
    ck = tmp_path / "pj.jsonl"
    ck.write_text(
        "\n".join([
            json.dumps({"model": ["m"], "prompt_id": "p1", "arm": "baseline", "score": 4.0}),
            json.dumps({"model": "m", "prompt_id": "p1", "arm": "baseline", "score": "nan"}),
            "{not-json",
        ]) + "\n",
        encoding="utf-8",
    )
    calls = {"n": 0}

    def judge(prompt, response, *, model):
        calls["n"] += 1
        return {"b": 4.0, "p": 5.0, "h": 8.0}[response[0]]

    rows = pj.run_judge({("m", "p1"): _arms()[("m", "p1")]}, judge_model="j", judge=judge, ckpt=ck, pace=0)

    assert calls["n"] == 3
    assert len(rows) == 3


def test_aggregate_contrasts():
    rows = []
    for pid in ("p1", "p2", "p3"):
        rows += [{"model": "m", "prompt_id": pid, "arm": "baseline", "score": 4.0},
                 {"model": "m", "prompt_id": pid, "arm": "placebo", "score": 5.0},
                 {"model": "m", "prompt_id": pid, "arm": "harnessed", "score": 8.0}]
    a = pj.aggregate(rows)
    ov = a["overall"]
    assert ov["n"] == 3
    assert ov["mean_baseline"] == 4.0 and ov["mean_placebo"] == 5.0 and ov["mean_harnessed"] == 8.0
    assert ov["placebo_minus_baseline"]["mean"] == 1.0
    assert ov["harnessed_minus_placebo"]["mean"] == 3.0      # the knowledge effect on the judge
    assert "m" in a["by_model"]


def test_aggregate_ignores_incomplete_triples():
    rows = [{"model": "m", "prompt_id": "p1", "arm": "baseline", "score": 4.0},
            {"model": "m", "prompt_id": "p1", "arm": "placebo", "score": 5.0},
            {"model": {"private": "worker@example.com"}, "prompt_id": "p2", "arm": "baseline", "score": 4.0},
            {"model": "m", "prompt_id": ["p2"], "arm": "placebo", "score": 5.0},
            {"model": "m", "prompt_id": "p2", "arm": "harnessed", "score": "nan"}]  # missing valid harnessed
    assert pj.aggregate(rows)["overall"] == {}


def test_build_report_renders(tmp_path):
    rows = []
    for pid in ("p1", "p2", "p3", "p4"):
        rows += [{"model": "m", "prompt_id": pid, "arm": "baseline", "score": 4.0},
                 {"model": "m", "prompt_id": pid, "arm": "placebo", "score": 5.0},
                 {"model": "m", "prompt_id": pid, "arm": "harnessed", "score": 8.0}]
    md = pj.build_report(pj.aggregate(rows), judge_model="gpt-oss:120b", out_path=tmp_path / "r.md")
    assert "Placebo control" in md and "harnessed − placebo" in md and "KNOWLEDGE effect" in md
