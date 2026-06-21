"""Tests for scripts/build_human_validation_sample.py -- blinded stratified sample + correlation."""
from __future__ import annotations

import csv
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


hv = _load("build_human_validation_sample", _ROOT / "scripts" / "build_human_validation_sample.py")


def _responses():
    out = []
    for pid in ("p1", "p2", "p3", "p4"):
        for arm in ("baseline", "harnessed"):
            out.append({"prompt_id": pid, "model": "m", "arm": arm, "response": f"reply {pid} {arm}"})
    return out


_CORPUS = {f"p{i}": {"text": f"worker msg {i}", "category": "cat" + str(i % 2), "difficulty": "hard"}
           for i in range(1, 5)}
_GRADER = {(f"p{i}", "m", arm): (8.0 if arm == "harnessed" else 4.0)
           for i in range(1, 5) for arm in ("baseline", "harnessed")}


def test_build_items_joins_and_keeps_complete():
    items = hv.build_items(_responses(), _CORPUS, _GRADER)
    assert len(items) == 8
    assert all(i["prompt_text"] and i["grader_score"] is not None and "category" in i for i in items)


def test_stratified_sample_is_seeded_and_blinded():
    items = hv.build_items(_responses(), _CORPUS, _GRADER)
    a = hv.stratified_sample(items, per_stratum=1, seed=13)
    b = hv.stratified_sample(hv.build_items(_responses(), _CORPUS, _GRADER), per_stratum=1, seed=13)
    assert [x["item_id"] for x in a] == [x["item_id"] for x in b]    # seeded -> reproducible
    assert all(x["item_id"].startswith("HV-") for x in a)


def test_export_blinds_arm_in_sheet_but_keeps_it_in_key(tmp_path):
    items = hv.build_items(_responses(), _CORPUS, _GRADER)
    picked = hv.stratified_sample(items, per_stratum=2, seed=7)
    sheet, key = hv.export(picked, out_dir=tmp_path)
    sheet_txt = sheet.read_text(encoding="utf-8")
    assert "expert_score" in sheet_txt and "rate this" in sheet_txt.lower()
    assert "harnessed" not in sheet_txt and "baseline" not in sheet_txt   # rater is blinded
    keymap = json.loads(key.read_text(encoding="utf-8"))
    assert keymap and all("arm" in v and "grader_score" in v for v in keymap.values())  # key has the truth


def test_spearman_and_correlate(tmp_path):
    assert abs(hv._spearman([1, 2, 3, 4], [1, 2, 3, 4]) - 1.0) < 1e-9
    # build a key + a ratings csv where human tracks grader -> spearman ~ 1
    key = {"HV-001": {"prompt_id": "p1", "model": "m", "arm": "baseline", "grader_score": 4.0},
           "HV-002": {"prompt_id": "p1", "model": "m", "arm": "harnessed", "grader_score": 8.0}}
    (tmp_path / "key.json").write_text(json.dumps(key), encoding="utf-8")
    with open(tmp_path / "r.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(["item_id", "expert_score"])
        w.writerow(["HV-001", "5"]); w.writerow(["HV-002", "9"])
    res = hv.correlate(tmp_path / "r.csv", key_path=tmp_path / "key.json")
    assert res["n"] == 2 and res["spearman"] == 1.0
