"""build_perdim_grades_dataset: exhaustive per-dimension grades -> versioned scores-only dataset."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location(
        "build_perdim_grades_dataset", _ROOT / "scripts" / "build_perdim_grades_dataset.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["build_perdim_grades_dataset"] = mod
    spec.loader.exec_module(mod)
    return mod


b = _load()

_ROWS = [
    {"model": "gemma4:31b", "prompt_id": "p1", "arm": "baseline", "judge": "glm-5.2",
     "score_0_100": 40.0, "grader": "perdim", "components": {"A": 30, "B": 40, "C": 50, "D": 45, "E": 35}},
    {"model": "gemma4:31b", "prompt_id": "p1", "arm": "harness_core", "judge": "glm-5.2",
     "score_0_100": 85.0, "grader": "perdim", "components": {"A": 90, "B": 80, "C": 88, "D": 84, "E": 83}},
]


def _panel(tmp_path):
    p = tmp_path / "panel_perdim.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in _ROWS) + "\n", encoding="utf-8")
    return p


def test_builds_scores_only_dataset(tmp_path):
    out = tmp_path / "out"
    res = b.build(out, panel=_panel(tmp_path), coverage=tmp_path / "missing.json")
    assert res["n_rows"] == 2 and res["n_prompts"] == 1
    ds = out / "dataset"
    csv_text = (ds / "perdim_grades.csv").read_text(encoding="utf-8")
    assert "comp_A" in csv_text and "comp_E" in csv_text and "score_0_100" in csv_text
    meta = json.loads((ds / "dataset-metadata.json").read_text(encoding="utf-8"))
    assert meta["isPrivate"] is False and meta["id"] == b.DATASET_ID
    manifest = json.loads((ds / "release-manifest.json").read_text(encoding="utf-8"))
    assert manifest["scores_only"] is True and manifest["contains_response_text_or_pii"] is False


def test_refuses_free_text_leak(tmp_path):
    leaky = dict(_ROWS[0])
    leaky["components"] = {"A": "x" * 300}  # a long string in a component -> must trip the guard
    p = tmp_path / "leak.jsonl"
    p.write_text(json.dumps(leaky) + "\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="free text"):
        b.build(tmp_path / "out", panel=p, coverage=tmp_path / "missing.json")
