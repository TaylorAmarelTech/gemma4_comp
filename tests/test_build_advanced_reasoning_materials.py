"""build_advanced_reasoning_materials: 100+ perspectives x 100+ step chain-of-thought, honest + safe,
and a contract-valid CoT training stream with a shared held-out split."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location(
        "build_advanced_reasoning_materials", _ROOT / "scripts" / "build_advanced_reasoning_materials.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["build_advanced_reasoning_materials"] = mod
    spec.loader.exec_module(mod)
    return mod


b = _load()


def test_100_plus_perspectives_across_nine_categories():
    keys = [p["key"] for p in b.PERSPECTIVES]
    assert len(keys) >= 100, f"need 100+ perspectives, got {len(keys)}"
    assert len(set(keys)) == len(keys), "perspective keys must be unique"
    cats = {p["category"] for p in b.PERSPECTIVES}
    assert cats == set(b.CATEGORIES), "every category must be represented"


def test_chain_of_thought_exceeds_100_steps():
    row = b.build_material(b.SITUATIONS[0], b.PERSPECTIVES[0], "large_jump", "outward")
    assert row["step_count"] >= 100, f"need a 100+ step chain, got {row['step_count']}"
    body = row["messages"][1]["content"]
    assert f"{row['step_count']}. " in body and "1. " in body


def test_all_11_ilo_indicators_screened_in_every_chain():
    body = b.build_material(b.SITUATIONS[0], b.PERSPECTIVES[0], "small_jump", "inward")["messages"][1]["content"]
    for key, _ in b.ILO_INDICATORS:
        assert key in body, f"indicator {key} missing from the chain"


def test_reach_and_direction_axes_change_the_chain():
    p, sit = b.PERSPECTIVES[0], b.SITUATIONS[0]
    a = b.build_material(sit, p, "small_jump", "inward")["messages"][1]["content"]
    c = b.build_material(sit, p, "large_jump", "outward")["messages"][1]["content"]
    assert a != c
    assert "small jump" in a and "large jump" in c
    assert "inward" in a and "outward" in c


def test_output_is_honest_and_safe(tmp_path):
    out = tmp_path / "cot.jsonl"
    summary = b.build(out, n_situations=5, n_perspectives=101, reach="large_jump", direction="outward")
    assert summary["contract_ok"] is True
    assert summary["train_rows"] > 0 and summary["holdout_rows"] > 0
    train = [json.loads(x) for x in out.read_text(encoding="utf-8").splitlines()]
    hold = [json.loads(x) for x in out.with_name("cot_holdout.jsonl").read_text(encoding="utf-8").splitlines()]
    blob = out.read_text(encoding="utf-8")
    # honours the naming request: never the "synthetic composite case" framing
    assert "synthetic composite" not in blob.lower()
    for r in train:
        assert r["split"] == "train"
        assert r["propose_only"] is True and "no real individual" in r["provenance"]
    # train and holdout share one lineage space but never overlap
    assert not ({r["lineage_id"] for r in train} & {r["lineage_id"] for r in hold})


def test_train_stream_passes_the_executable_contract(tmp_path):
    out = tmp_path / "cot.jsonl"
    b.build(out, n_situations=5, n_perspectives=101, reach="large_jump", direction="outward")
    contract = b._contract()
    train = [json.loads(x) for x in out.read_text(encoding="utf-8").splitlines()]
    hold = [json.loads(x) for x in out.with_name("cot_holdout.jsonl").read_text(encoding="utf-8").splitlines()]
    eval_lineages = sorted({r["lineage_id"] for r in hold})
    eval_hashes = sorted({contract.canonical_sha256(r["messages"][0]["content"]) for r in hold})
    report = contract.validate_training_rows(
        train, evaluation_prompt_hashes=eval_hashes, evaluation_lineage_ids=eval_lineages)
    assert report["ok"], report["blocking_failures"]
    # row integrity: every sha256 is the contract's own canonical digest
    assert all(r["sha256"] == contract.training_row_sha256(r) for r in train)
