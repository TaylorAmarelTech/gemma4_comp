"""Tests for scripts/comparative_results.py -- the per-model harness-lift leaderboard."""
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


cr = _load("comparative_results", _ROOT / "scripts" / "comparative_results.py")


def _cells():
    rows = []
    # model_a: big lift (+3 each prompt); model_b: small lift (+1 each prompt)
    for pid in ("p1", "p2", "p3"):
        rows += [
            {"model": "model_a", "prompt_id": pid, "arm": "baseline", "dim": "d", "score": 4.0},
            {"model": "model_a", "prompt_id": pid, "arm": "harnessed", "dim": "d", "score": 7.0},
            {"model": "model_b", "prompt_id": pid, "arm": "baseline", "dim": "d", "score": 6.0},
            {"model": "model_b", "prompt_id": pid, "arm": "harnessed", "dim": "d", "score": 7.0},
        ]
    return rows


def test_load_cells_roundtrip(tmp_path):
    p = tmp_path / "c.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in _cells()) + "\n", encoding="utf-8")
    cells = cr.load_cells([p])
    assert len(cells) == 12


def test_pooled_deltas_counts_every_pair():
    d = cr.pooled_deltas(_cells())
    assert len(d) == 6                       # 2 models x 3 prompts
    assert round(sum(d) / len(d), 2) == 2.0  # mean of (+3,+3,+3,+1,+1,+1)


def test_dim_improve_regress_is_ceiling_robust():
    ir = cr.dim_improve_regress(_cells())
    # both models improve their single dimension; neither regresses
    assert ir["model_a"]["improved"] == 1 and ir["model_a"]["regressed"] == 0
    assert ir["model_b"]["improved"] == 1 and ir["model_b"]["regressed"] == 0
    assert round(ir["model_a"]["mean_lift_improved"], 2) == 3.0


def test_deterministic_mode_is_conservative_with_ceiling_framing(tmp_path):
    md = cr.build_report(_cells(), out_path=tmp_path / "r.md", mode="deterministic")
    assert "Comparative results" in md
    assert md.index("model_a") < md.index("model_b")               # bigger lift ranks first
    for col in ("Baseline", "Harnessed", "Lift", "95% CI", "Dims ↑ / ↓"):
        assert col in md
    assert "ceiling effect" in md.lower()                          # honest conservative framing
    assert "conservative" in md.lower() or "cross-check" in md.lower()


def test_llm_judge_mode_is_primary_and_not_ceiling_framed(tmp_path):
    md = cr.build_report(_cells(), out_path=tmp_path / "r.md", mode="llm_judge")
    assert "LLM-judge" in md and "primary" in md.lower()
    assert "holistically" in md.lower()                            # the non-rigid framing
    assert md.index("model_a") < md.index("model_b")
    assert "Cohen's d" in md and "Win %" in md
