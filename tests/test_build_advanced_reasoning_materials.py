"""build_advanced_reasoning_materials: 100+ perspectives x 100+ step chain-of-thought, honest + safe."""
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
    sit = b.SITUATIONS[0]
    p = b.PERSPECTIVES[0]
    row = b.build_material(sit, p, "large_jump", "outward")
    assert row["step_count"] >= 100, f"need a 100+ step chain, got {row['step_count']}"
    body = row["messages"][1]["content"]
    # steps are numbered 1..N and the last number equals the step count
    assert f"{row['step_count']}. " in body
    assert "1. " in body


def test_all_11_ilo_indicators_screened_in_every_chain():
    row = b.build_material(b.SITUATIONS[0], b.PERSPECTIVES[0], "small_jump", "inward")
    body = row["messages"][1]["content"]
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
    out = tmp_path / "materials.jsonl"
    summary = b.build(out, n_situations=2, n_perspectives=101, reach="large_jump", direction="outward")
    assert summary["rows"] == 2 * 101
    rows = [json.loads(x) for x in out.read_text(encoding="utf-8").splitlines()]
    blob = out.read_text(encoding="utf-8")
    # honours the naming request: never the "synthetic composite case" framing
    assert "synthetic composite" not in blob.lower()
    for r in rows:
        assert r["propose_only"] is True
        assert "no real individual" in r["provenance"]
        assert r["sha256"] and len(r["sha256"]) == 64
        assert [m["role"] for m in r["messages"]] == ["user", "assistant"]
