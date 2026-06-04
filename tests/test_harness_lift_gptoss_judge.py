"""Tests for the scalable gpt-oss judge (fake model_call, no keys/network)."""
from __future__ import annotations

import importlib
import json
import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SCRIPTS = _ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

gj = importlib.import_module("harness_lift_gptoss_judge")
from harness_lift_scheduled import aggregate  # noqa: E402


def test_parse_scorecard_keeps_valid_ids_and_clamps():
    out = gj.parse_scorecard('```json\n{"a.x": 9, "b.y": 12, "bogus": 4, "c.z": -1}\n```',
                             {"a.x", "b.y", "c.z"})
    assert out["a.x"] == 9.0
    assert out["b.y"] == 10.0   # clamped
    assert out["c.z"] == 0.0    # clamped
    assert "bogus" not in out


def test_run_writes_cells_and_is_resumable(tmp_path, monkeypatch):
    # Minimal fixture: one prompt, both arms; fake judge scores 2 dims.
    bench = tmp_path / "bench"
    bench.mkdir()
    (bench / "harness_lift_dimensions.json").write_text(json.dumps({"dimensions": [
        {"id": "response_quality.a", "group": "response_quality", "question": "q1"},
        {"id": "explanatory_refusal.b", "group": "explanatory_refusal", "question": "q2"}]}), encoding="utf-8")
    (bench / "p.json").write_text(json.dumps({"prompts": [{"id": "p1", "text": "worker msg",
                                                           "category": "rights_query"}]}), encoding="utf-8")
    monkeypatch.setattr(gj, "_BENCH", bench)
    monkeypatch.setattr(gj.oj, "_BENCH", bench)
    resp = tmp_path / "resp.jsonl"
    resp.write_text("\n".join(json.dumps(r) for r in [
        {"prompt_id": "p1", "model": "gemma", "arm": "baseline", "response": "bad"},
        {"prompt_id": "p1", "model": "gemma", "arm": "harnessed", "response": "good"}]), encoding="utf-8")
    ckpt = tmp_path / "judge.jsonl"
    fake = lambda _t: '{"response_quality.a": 7, "explanatory_refusal.b": 8}'
    n = gj.run(resp, ckpt, "p.json", model_call=fake)
    assert n == 4                                   # 2 responses x 2 dims
    assert gj.run(resp, ckpt, "p.json", model_call=fake) == 0   # resumable
    agg = aggregate(ckpt)
    assert agg["total_cells"] == 4
