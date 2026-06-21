"""Tests for scripts/applicability_audit.py -- applicability gate validation + multi-pass."""
from __future__ import annotations

import importlib.util
import random
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


aa = _load("applicability_audit", _ROOT / "scripts" / "applicability_audit.py")


def _grade_fake(prompt, response):
    return [
        {"id": "d_app1", "name": "A1", "description": "check 1", "status": "PASS", "score_0_10": 7},
        {"id": "d_app2", "name": "A2", "description": "check 2", "status": "FAIL", "score_0_10": 2},
        {"id": "d_na1", "name": "N1", "description": "check 3", "status": "NOT_APPLICABLE"},
        {"id": "d_na2", "name": "N2", "description": "check 4", "status": "NOT_APPLICABLE"},
    ]


def test_grader_decisions_maps_status_to_applicable():
    d = aa.grader_decisions("p", "r", grade=_grade_fake)
    assert d["d_app1"]["applicable"] is True and d["d_app1"]["name"] == "A1"
    assert d["d_na1"]["applicable"] is False


def test_judge_applicability_is_multipass():
    cap = []

    def caller(text, **_kw):
        cap.append(text)
        return '{"relevant": true}'

    v = aa.judge_applicability("p", "A1", "desc", model="m", caller=caller, passes=3)
    assert v["votes"] == [True, True, True] and v["applicable"] and v["unanimous"]
    assert len(cap) == 3                                  # genuinely 3 passes
    seq = iter(['{"relevant": true}', '{"relevant": false}', '{"relevant": true}'])
    v2 = aa.judge_applicability("p", "A1", "d", model="m", caller=lambda t, **k: next(seq), passes=3)
    assert v2["applicable"] is True and v2["unanimous"] is False   # 2/3 yes, not unanimous


def test_cohens_kappa():
    assert aa.cohens_kappa([True, True, False, False], [True, True, False, False]) == 1.0
    assert aa.cohens_kappa([True, False, True, False], [False, True, False, True]) < 0  # anti-agree


def test_stratified_pairs_balances_sides():
    d = aa.grader_decisions("p", "r", grade=_grade_fake)
    pairs = aa.stratified_pairs(d, per_side=1, rng=random.Random(0))
    apps = [k for k, v in pairs if v["applicable"]]
    nas = [k for k, v in pairs if not v["applicable"]]
    assert len(apps) == 1 and len(nas) == 1


def test_run_aggregate_report_and_resume(tmp_path):
    prompts = [{"id": "P1", "text": "msg one"}, {"id": "P2", "text": "msg two"}]
    ck = tmp_path / "aa.jsonl"
    rows = aa.run(prompts, grade=_grade_fake, judge_caller=lambda t, **k: '{"relevant": true}',
                  judge_model="m", dims_per_side=1, passes=3, ckpt=ck, pace=0)
    assert len(rows) == 4                                 # 2 prompts x (1 applicable + 1 NA)
    a = aa.aggregate(rows)
    assert a["n"] == 4 and 0.0 <= a["raw_agreement"] <= 1.0
    md = aa.build_report(rows, judge_model="m", passes=3, out_path=tmp_path / "r.md")
    assert "Applicability verification" in md and "κ" in md
    rows2 = aa.run(prompts, grade=_grade_fake, judge_caller=lambda t, **k: '{"relevant": true}',
                   judge_model="m", dims_per_side=1, passes=3, ckpt=ck, pace=0)
    assert len(rows2) == 4                                # all done; no rework
