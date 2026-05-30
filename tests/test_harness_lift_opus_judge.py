"""Tests for the Opus-judge pipeline plumbing (make_batches / ingest / group agg).

The judging itself is done by Opus subagents; this covers the deterministic
plumbing with synthetic batch + scorecard files (no agents, no keys).
"""
from __future__ import annotations

import importlib
import json
import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SCRIPTS = _ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

opus = importlib.import_module("harness_lift_opus_judge")
from harness_lift_scheduled import aggregate  # noqa: E402


def _write_scorecard(tmp_path, name, cards):
    opus._SCORECARD_DIR.mkdir(parents=True, exist_ok=True)
    (opus._SCORECARD_DIR / name).write_text(json.dumps({"scorecards": cards}), encoding="utf-8")


def test_ingest_folds_scores_and_skips_nulls_and_dupes(tmp_path, monkeypatch):
    # Isolate the scorecard dir + checkpoint to tmp.
    monkeypatch.setattr(opus, "_SCORECARD_DIR", tmp_path / "sc")
    ckpt = tmp_path / "opus.jsonl"
    _write_scorecard(tmp_path, "batch_0000.json", [
        {"prompt_id": "p1", "model": "m", "arm": "baseline",
         "scores": {"ilo_indicator.deception": 3.0, "response_quality.x": None}},
        {"prompt_id": "p1", "model": "m", "arm": "harnessed",
         "scores": {"ilo_indicator.deception": 9.0, "response_quality.x": 8.0}},
    ])
    agg = opus.ingest(ckpt)
    # null excluded -> baseline contributes 1 cell, harnessed 2
    row = next(r for r in agg["ranked_by_lift"] if r["model"] == "m")
    assert row["baseline_mean"] == 3.0
    assert row["harnessed_mean"] == 8.5   # (9 + 8) / 2
    assert row["lift"] == 5.5
    assert agg["total_cells"] == 3

    # Re-ingest the same scorecard -> idempotent (cells already present).
    agg2 = opus.ingest(ckpt)
    assert agg2["total_cells"] == 3


def test_aggregate_by_group_splits_on_dim_prefix(tmp_path, monkeypatch):
    monkeypatch.setattr(opus, "_SCORECARD_DIR", tmp_path / "sc")
    ckpt = tmp_path / "opus.jsonl"
    _write_scorecard(tmp_path, "b.json", [
        {"prompt_id": "p1", "model": "m", "arm": "baseline",
         "scores": {"ilo_indicator.a": 2.0, "scheme_detection.b": 4.0}},
        {"prompt_id": "p1", "model": "m", "arm": "harnessed",
         "scores": {"ilo_indicator.a": 8.0, "scheme_detection.b": 6.0}},
    ])
    opus.ingest(ckpt)
    by = opus.aggregate_by_group(ckpt)
    groups = {r["group"]: r for r in by["m"]}
    assert groups["ilo_indicator"]["lift"] == 6.0   # 8 - 2
    assert groups["scheme_detection"]["lift"] == 2.0  # 6 - 4
