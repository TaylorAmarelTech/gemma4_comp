"""Tests for scripts/build_frontier_perdim_report.py -- per-dimension lift aggregation + report.

Offline: synthetic per-dimension cells, no network. Verifies the per-dimension lift, the
improve/neutral/regress split, the cell loader's filtering, and the rendered report.
"""
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


def test_per_dimension_deltas_pairs_harnessed_minus_baseline():
    cells = []
    for pid in ("p1", "p2"):
        cells += [{"model": "m", "prompt_id": pid, "arm": "baseline", "dim": "A", "score": 4.0},
                  {"model": "m", "prompt_id": pid, "arm": "harnessed", "dim": "A", "score": 6.0}]
    assert b.per_dimension_deltas(cells)["A"] == [2.0, 2.0]


def test_paired_test_and_benjamini_hochberg():
    import lift_stats as ls                              # scripts/ is on sys.path via the builder load
    sig = ls.paired_test([2.0, 1.0, 3.0] * 10)           # mean 2 with real variance, n=30
    assert sig["p"] < 0.05 and sig["mean"] > 0
    null = ls.paired_test([0.2, -0.2, 0.1, -0.1] * 8)    # mean ~ 0
    assert null["p"] > 0.05
    bh = ls.benjamini_hochberg({"a": 0.0001, "b": 0.6, "c": 0.03})
    assert bh["a"]["significant"] is True and bh["b"]["significant"] is False
    assert bh["a"]["q"] <= bh["c"]["q"] <= bh["b"]["q"]   # BH q-values are monotone in p


def test_load_cells_skips_safety_judge_rows_and_nulls(tmp_path):
    p = tmp_path / "c.jsonl"
    p.write_text("\n".join([
        '{"model": "m", "prompt_id": "p", "arm": "baseline", "dim": "A", "score": 4}',
        '{"model": "m", "prompt_id": "p", "arm": "baseline", "dim": "safety", "score": 9}',
        '{"model": "m", "prompt_id": "p", "arm": "baseline", "dim": "A", "score": null}',
        '{"model": "m", "prompt_id": "p", "arm": "other", "dim": "A", "score": 4}',
        '{"model": "m", "prompt_id": "p", "arm": "baseline", "dim": "A", "score": "nan"}',
        '{"prompt_id": "p", "arm": "baseline", "dim": "A", "score": 4}',
        '{"model": {"private": "worker@example.com"}, "prompt_id": "p", "arm": "baseline", "dim": "A", "score": 4}',
        '{"model": "m", "prompt_id": ["p"], "arm": "baseline", "dim": "A", "score": 4}',
        '{"model": "m", "prompt_id": "p", "arm": {"private": "baseline"}, "dim": "A", "score": 4}',
        '{"model": "m", "prompt_id": "p", "arm": "baseline", "dim": {"private": "worker@example.com"}, "score": 4}',
        '["not", "an", "object"]',
        "not valid json",
    ]), encoding="utf-8")
    cells = b.load_cells(p)
    assert len(cells) == 1 and cells[0]["dim"] == "A"   # safety row + null score + junk dropped


def test_build_report_redacts_sensitive_model_and_dimension_labels(tmp_path):
    sensitive = "worker@example.com-case-123456789"
    cells = []
    for row in _cells():
        row = dict(row)
        row["model"] = sensitive
        row["dim"] = sensitive if row["dim"] == "A" else row["dim"]
        cells.append(row)

    md = b.build_report(cells, judge_note="x", out_path=tmp_path / "r.md")

    assert sensitive not in md
    assert "`redacted`" in md


def test_main_success_console_redacts_sensitive_output_path(tmp_path, capsys):
    ckpt = tmp_path / "perdim.jsonl"
    ckpt.write_text("\n".join(json.dumps(row) for row in _cells()), encoding="utf-8")
    out = tmp_path / "worker@example.com-case-123456789" / "frontier_perdim.md"

    assert b.main(["--ckpt", str(ckpt), "--out", str(out)]) == 0

    printed = capsys.readouterr().err
    assert out.exists()
    assert "report -> external" in printed
    assert str(tmp_path) not in printed
    assert "worker@example.com" not in printed
    assert "case-123456789" not in printed


def test_main_missing_cells_console_redacts_sensitive_checkpoint_path(tmp_path, capsys):
    ckpt = tmp_path / "worker@example.com-case-123456789" / "missing.jsonl"

    assert b.main(["--ckpt", str(ckpt), "--out", str(tmp_path / "out.md")]) == 1

    printed = capsys.readouterr().err
    assert "no per-dimension cells in external" in printed
    assert str(tmp_path) not in printed
    assert "worker@example.com" not in printed
    assert "case-123456789" not in printed
