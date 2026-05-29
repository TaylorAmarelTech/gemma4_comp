"""Tests for the scheduled, resumable, per-dimension harness-lift runner."""
from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = str(Path(__file__).resolve().parents[1] / "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import harness_lift_scheduled as hls  # noqa: E402

PROMPTS = [{"id": "p1", "text": "a loan and my passport is held"}, {"id": "p2", "text": "hello"}]
CANDS = [{"model": "m1"}, {"model": "m2"}]
DIMS = [{"id": "law"}, {"id": "refusal"}, {"id": "referral"}]


def _preamble(_text):
    return "SAFETY GROUNDING: cite ILO, refuse exploitation, refer to resources."


def _gen(_model, prompt):
    return "good" if "SAFETY GROUNDING" in prompt else "weak"


def _grade(_prompt, resp, _dim):
    return 9.0 if resp == "good" else 5.0


def test_runs_all_cells_and_aggregates_lift(tmp_path):
    cp = tmp_path / "ckpt.jsonl"
    n = hls.run_scheduled(PROMPTS, CANDS, DIMS, build_preamble=_preamble,
                          generate=_gen, grade_dim=_grade, checkpoint_path=cp)
    # 2 prompts x 2 models x 2 arms x 3 dims = 24 cells
    assert n == 24
    agg = hls.aggregate(cp)
    assert agg["total_cells"] == 24
    assert len(agg["ranked_by_lift"]) == 2
    for row in agg["ranked_by_lift"]:
        assert row["lift"] == 4.0  # harnessed 9.0 - baseline 5.0
        assert row["n_cells_baseline"] == 6 and row["n_cells_harnessed"] == 6


def test_resume_skips_completed_with_no_regeneration(tmp_path):
    cp = tmp_path / "ckpt.jsonl"
    hls.run_scheduled(PROMPTS, CANDS, DIMS, build_preamble=_preamble,
                      generate=_gen, grade_dim=_grade, checkpoint_path=cp)
    calls: list[int] = []

    def gen2(m, p):
        calls.append(1)
        return _gen(m, p)

    n2 = hls.run_scheduled(PROMPTS, CANDS, DIMS, build_preamble=_preamble,
                           generate=gen2, grade_dim=_grade, checkpoint_path=cp)
    assert n2 == 0 and calls == []  # fully resumed: no new cells, no model calls


def test_partial_resume_runs_only_new_dimensions(tmp_path):
    cp = tmp_path / "ckpt.jsonl"
    hls.run_scheduled(PROMPTS, CANDS, DIMS[:1], build_preamble=_preamble,
                      generate=_gen, grade_dim=_grade, checkpoint_path=cp)
    first = hls.aggregate(cp)["total_cells"]  # 2x2x2x1 = 8
    n2 = hls.run_scheduled(PROMPTS, CANDS, DIMS, build_preamble=_preamble,
                           generate=_gen, grade_dim=_grade, checkpoint_path=cp)
    assert first == 8 and n2 == 16  # only the 2 new dims graded
    assert hls.aggregate(cp)["total_cells"] == 24
