"""Tests for scripts/build_frontier_perdim_report.py -- per-dimension lift aggregation + report.

Offline: synthetic per-dimension cells, no network. Verifies the per-dimension lift, the
improve/neutral/regress split, the cell loader's filtering, and the rendered report.
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


b = _load("build_frontier_perdim_report", _ROOT / "scripts" / "build_frontier_perdim_report.py")


def _cells():
    out = []
    for pid in ("p1", "p2", "p3"):
        out += [
            {"model": "m", "prompt_id": pid, "arm": "baseline", "dim": "A", "score": 4.0},
            {"model": "m", "prompt_id": pid, "arm": "harnessed", "dim": "A", "score": 6.0},   # +2 improve
            {"model": "m", "prompt_id": pid, "arm": "baseline", "dim": "B", "score": 8.0},
            {"model": "m", "prompt_id": pid, "arm": "harnessed", "dim": "B", "score": 7.0},   # -1 regress
            {"model": "m", "prompt_id": pid, "arm": "baseline", "dim": "C", "score": 5.0},
            {"model": "m", "prompt_id": pid, "arm": "harnessed", "dim": "C", "score": 5.0},   # neutral
        ]
    return out


def test_per_dimension_lift_pairs_same_dim_both_arms():
    dl = b.per_dimension_lift(_cells())
    assert dl["A"][2] == 2.0 and dl["B"][2] == -1.0 and dl["C"][2] == 0.0
    assert dl["A"][3] == 3                       # n pairs


def test_counts_split_improve_neutral_regress():
    imp, neu, reg = b._counts(b.per_dimension_lift(_cells()))
    assert [d for d, _ in imp] == ["A"]
    assert [d for d, _ in reg] == ["B"]
    assert [d for d, _ in neu] == ["C"]


def test_build_report_states_counts_and_shows_regressions(tmp_path):
    md = b.build_report(_cells(), judge_note="x", out_path=tmp_path / "r.md")
    assert "improves 1 of 3 graded rubric dimensions" in md
    assert "regresses 1" in md
    assert "`A`" in md and "`B`" in md           # both the improved + the regressed dim are tabled
    assert "honest tradeoffs" in md.lower()


def test_load_cells_skips_safety_judge_rows_and_nulls(tmp_path):
    p = tmp_path / "c.jsonl"
    p.write_text("\n".join([
        '{"model": "m", "prompt_id": "p", "arm": "baseline", "dim": "A", "score": 4}',
        '{"model": "m", "prompt_id": "p", "arm": "baseline", "dim": "safety", "score": 9}',
        '{"model": "m", "prompt_id": "p", "arm": "baseline", "dim": "A", "score": null}',
        "not valid json",
    ]), encoding="utf-8")
    cells = b.load_cells(p)
    assert len(cells) == 1 and cells[0]["dim"] == "A"   # safety row + null score + junk dropped
