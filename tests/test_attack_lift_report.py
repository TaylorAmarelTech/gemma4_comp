"""Tests for scripts/attack_lift_report.py -- harness lift per attack transform."""
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


alr = _load("attack_lift_report", _ROOT / "scripts" / "attack_lift_report.py")


def test_transform_map(tmp_path):
    m = tmp_path / "matrix.json"
    m.write_text(json.dumps({"prompts": [{"id": "ATK-1", "transform": "base64"},
                                         {"id": "ATK-2", "transform": "homoglyph"}]}), encoding="utf-8")
    assert alr.transform_map(m) == {"ATK-1": "base64", "ATK-2": "homoglyph"}


def test_paired_lifts_and_aggregate(tmp_path):
    tmap = {"p1": "base64", "p2": "base64", "p3": "homoglyph"}
    j = tmp_path / "judge.jsonl"
    rows = [{"prompt_id": "p1", "arm": "baseline", "score": 3}, {"prompt_id": "p1", "arm": "harnessed", "score": 7},
            {"prompt_id": "p2", "arm": "baseline", "score": 2}, {"prompt_id": "p2", "arm": "harnessed", "score": 8},
            {"prompt_id": "p3", "arm": "baseline", "score": 5}, {"prompt_id": "p3", "arm": "harnessed", "score": 6}]
    j.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    by, overall = alr.paired_lifts(j, tmap)
    assert by["base64"] == [4.0, 6.0] and by["homoglyph"] == [1.0]
    assert len(overall) == 3
    agg = alr.aggregate(by, overall)
    assert agg["all_positive"] is True
    b64 = next(r for r in agg["rows"] if r["transform"] == "base64")
    assert b64["lift"] == 5.0 and b64["n"] == 2          # (4+6)/2


def test_build_report_highlights_encoding_backstop(tmp_path):
    by = {"base64": [3.9, 4.1], "rot13": [3.8, 3.8], "homoglyph": [4.4, 4.5]}
    overall = sum(by.values(), [])
    md = alr.build_report(alr.aggregate(by, overall), out_path=tmp_path / "r.md")
    assert "Lift under attack" in md and "encoding" in md.lower()
    assert "`base64`" in md and "carrying the safety" in md
