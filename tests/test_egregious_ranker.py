"""Tests for scripts/egregious_ranker.py -- surface the worst baseline replies for human review."""
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


er = _load("egregious_ranker", _ROOT / "scripts" / "egregious_ranker.py")


def test_load_responses_keeps_arms_and_joins_text(tmp_path):
    p = tmp_path / "r.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in [
        {"model": "m", "prompt_id": "p1", "arm": "baseline", "prompt_text": "q", "response": "a"},
        {"model": "m", "prompt_id": "p1", "arm": "harnessed", "prompt_text": "q", "response": "b"},
        {"model": "m", "prompt_id": "p1", "arm": "other", "prompt_text": "q", "response": "c"},  # dropped
    ]) + "\n", encoding="utf-8")
    out = er.load_responses([p])
    assert ("p1", "m", "baseline") in out and ("p1", "m", "harnessed") in out
    assert ("p1", "m", "other") not in out


def test_prefilter_ranks_substantive_low_safety_baseline():
    responses = {
        ("p1", "m", "baseline"): {"prompt_text": "q1", "response": "X" * 1500},   # long, unsafe
        ("p1", "m", "harnessed"): {"prompt_text": "q1", "response": "good reply"},
        ("p2", "m", "baseline"): {"prompt_text": "q2", "response": "Y" * 1500},    # long, safe
        ("p3", "m", "baseline"): {"prompt_text": "q3", "response": "short"},       # too short -> excluded
    }
    grade = lambda prompt, resp: 2.0 if prompt == "q1" else 8.0  # noqa: E731
    cands = er.deterministic_prefilter(responses, grade=grade, top_k=10)
    assert [c["prompt_id"] for c in cands] == ["p1", "p2"]       # unsafe first; short excluded
    assert cands[0]["harnessed"] == "good reply"                  # harnessed contrast attached


def test_length_prefilter_picks_longest_baseline_no_grading():
    responses = {
        ("p1", "m", "baseline"): {"prompt_text": "q1", "response": "X" * 1500},   # longest
        ("p2", "m", "baseline"): {"prompt_text": "q2", "response": "Y" * 600},
        ("p3", "m", "baseline"): {"prompt_text": "q3", "response": "short"},       # excluded
        ("p1", "m", "harnessed"): {"prompt_text": "q1", "response": "h"},
    }
    cands = er.length_prefilter(responses, top_k=10)
    assert [c["prompt_id"] for c in cands] == ["p1", "p2"]        # longest first; short dropped
    assert cands[0]["safety_score"] is None                       # no deterministic grade done
    assert cands[0]["harnessed"] == "h"


def test_judge_egregiousness_parses_and_clamps():
    v = er.judge_egregiousness("p", "r", model="m", caller=lambda t, **k: (
        '{"egregiousness": 9, "harm_type": "enables_exploitation", '
        '"worst_quote": "hold their passports", "why": "tells the exploiter how"}'))
    assert v["egregiousness"] == 9.0 and v["harm_type"] == "enables_exploitation"
    assert v["worst_quote"] == "hold their passports"


def test_rank_with_judge_orders_by_egregiousness_and_resumes(tmp_path):
    cands = [{"prompt_id": "p1", "model": "m", "prompt_text": "q", "response": "r1", "harnessed": "h"},
             {"prompt_id": "p2", "model": "m", "prompt_text": "q", "response": "r2", "harnessed": ""}]
    caller = lambda t, **k: ('{"egregiousness": 9}' if "r1" in t else '{"egregiousness": 4}')  # noqa: E731
    ck = tmp_path / "er.jsonl"
    ranked = er.rank_with_judge(cands, judge_model="m", caller=caller, ckpt=ck, pace=0)
    assert [c["prompt_id"] for c in ranked] == ["p1", "p2"] and ranked[0]["egregiousness"] == 9.0
    # resume: reuses ckpt, does not re-judge
    ranked2 = er.rank_with_judge(cands, judge_model="m", caller=lambda t, **k: '{"egregiousness": 0}',
                                 ckpt=ck, pace=0)
    assert ranked2[0]["egregiousness"] == 9.0


def test_build_report_judged_and_prefilter(tmp_path):
    ranked = [{"prompt_id": "p1", "model": "m", "prompt_text": "q", "response": "r" * 500,
               "harnessed": "h" * 500, "safety_score": 2.0, "det_egregiousness": 8.0,
               "egregiousness": 9.0, "harm_type": "enables_exploitation",
               "worst_quote": "hold their passports", "why": "enables the exploiter"}]
    md = er.build_report(ranked, judged=True, top_n=10, judge_model="gpt-oss:120b",
                         out_path=tmp_path / "r.md")
    assert "Egregious responses" in md and "enables_exploitation" in md
    assert "hold their passports" in md and "Harnessed reply" in md
    md2 = er.build_report(ranked, judged=False, top_n=10, judge_model="", out_path=tmp_path / "r2.md")
    assert "pre-filter only" in md2.lower()
