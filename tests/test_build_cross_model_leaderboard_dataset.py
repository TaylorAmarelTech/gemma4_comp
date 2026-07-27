"""build_cross_model_leaderboard_dataset: package the board JSON as a citable Kaggle dataset."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location(
        "build_cross_model_leaderboard_dataset", _ROOT / "scripts" / "build_cross_model_leaderboard_dataset.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["build_cross_model_leaderboard_dataset"] = mod
    spec.loader.exec_module(mod)
    return mod


b = _load()

_BOARD = {
    "benchmark": {"id": "duecare-harness-lift"},
    "judges": ["j1", "j2", "j3"],
    "git_sha": "abcdef1234",
    "models": [
        {"rank": 1, "model": "big:31b", "n_prompts": 1000, "n_observations": 3000,
         "baseline": 48.0, "harness_core": 89.0, "harnessed": 88.0, "lift": 40.0, "lift_core": 41.0,
         "normalized_gain": 0.74, "pairwise_full_vs_core": 0.1,
         "components_gain": {"A": 8.7, "B": 8.9, "C": 6.7, "D": 7.8, "E": 8.7}},
        {"rank": 2, "model": "small:2b", "n_prompts": 5, "n_observations": 15,
         "baseline": 30.0, "harness_core": 28.0, "harnessed": 27.0, "lift": -3.0, "lift_core": -2.0,
         "normalized_gain": -0.05, "pairwise_full_vs_core": None, "components_gain": {"A": -1.7}},
    ],
}


def _build(tmp_path):
    board_path = tmp_path / "board.json"
    board_path.write_text(json.dumps(_BOARD), encoding="utf-8")
    out = tmp_path / "out"
    result = b.build(out, board_path=board_path)
    return out / "dataset", result


def test_emits_flat_csv_with_all_fields(tmp_path):
    ds, result = _build(tmp_path)
    assert result["n_models"] == 2
    csv_text = (ds / "leaderboard.csv").read_text(encoding="utf-8")
    header = csv_text.splitlines()[0]
    for col in ("rank", "model", "baseline", "harnessed", "lift", "normalized_gain",
                "comp_gain_A_indicator", "comp_gain_E_privacy"):
        assert col in header
    # the honest negative-lift small model survives into the CSV (not hidden)
    assert "small:2b" in csv_text and "-3.0" in csv_text


def test_manifest_flags_no_pii_and_binds_shas(tmp_path):
    ds, _ = _build(tmp_path)
    manifest = json.loads((ds / "release-manifest.json").read_text(encoding="utf-8"))
    assert manifest["contains_raw_grades_or_pii"] is False
    assert manifest["n_models"] == 2
    assert set(manifest["artifacts"]) == {"leaderboard.csv", "leaderboard.json", "README.md"}
    for meta in manifest["artifacts"].values():
        assert len(meta["sha256"]) == 64 and meta["bytes"] > 0


def test_metadata_subtitle_within_kaggle_limits(tmp_path):
    ds, _ = _build(tmp_path)
    meta = json.loads((ds / "dataset-metadata.json").read_text(encoding="utf-8"))
    assert 20 <= len(meta["subtitle"]) <= 80          # Kaggle subtitle bound
    assert len(meta["keywords"]) <= 6                  # Kaggle keyword cap
    assert meta["id"] == b.DATASET_ID
