"""Tests for scripts/benchmark_leaderboard.py -- the harness-lift benchmark leaderboard (offline)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


sys.path.insert(0, str(_ROOT / "scripts"))
for _s in _ROOT.glob("packages/*/src"):
    sys.path.insert(0, str(_s))
bl = _load("benchmark_leaderboard", _ROOT / "scripts" / "benchmark_leaderboard.py")


def _panel(model, base, full, cb, cf, judges=("j1", "j2"), pids=("p1", "p2")):
    rows = []
    for j in judges:
        for pid in pids:
            rows.append({"model": model, "arm": "baseline", "prompt_id": pid, "judge": j,
                         "score_0_100": base, "components": cb})
            rows.append({"model": model, "arm": "harness_full", "prompt_id": pid, "judge": j,
                         "score_0_100": full, "components": cf})
    return rows


_CB = {"A": 14, "B": 3, "C": 24, "D": 0, "E": 2}
_CF = {"A": 24, "B": 18, "C": 25, "D": 12, "E": 12}


def test_leaderboard_ranks_by_lift_and_per_criterion():
    panel = _panel("model-low", 60, 80, _CB, _CF) + _panel("model-high", 40, 90, _CB, _CF)
    rows = bl.leaderboard_rows(panel, [])
    assert [r["model"] for r in rows] == ["model-high", "model-low"]   # ranked by lift desc
    assert rows[0]["rank"] == 1 and rows[0]["lift"] == 50.0
    assert rows[1]["lift"] == 20.0
    # per-criterion gain: B = 18-3 = +15, D = 12-0 = +12 (the lift-driving criteria)
    assert rows[0]["components_gain"]["B"] == 15.0 and rows[0]["components_gain"]["D"] == 12.0
    assert rows[0]["n_prompts"] == 2


def test_pairwise_folded_in_and_only_complete_arms_count():
    panel = _panel("m", 40, 90, _CB, _CF)
    pw = [{"model": "m", "prompt_id": "p1", "judge": "j1", "delta": 2.0},
          {"model": "m", "prompt_id": "p2", "judge": "j1", "delta": 1.0}]
    rows = bl.leaderboard_rows(panel, pw)
    assert rows[0]["pairwise_full_vs_core"] == 1.5
    # a model with only a baseline arm (no harness_full) is excluded from the leaderboard
    panel2 = [{"model": "x", "arm": "baseline", "prompt_id": "p1", "judge": "j1",
               "score_0_100": 50, "components": _CB}]
    assert bl.leaderboard_rows(panel2, []) == []


def test_build_and_render_carry_spec_provenance_and_lift():
    panel = _panel("m", 40, 90, _CB, _CF)
    lb = bl.build_leaderboard(panel, [], generated="2026-06-23T00:00:00Z", sha="abc1234")
    assert lb["benchmark"]["id"] == "duecare-harness-lift" and lb["benchmark"]["version"] == "1.3"
    assert lb["judges"] == ["j1", "j2"] and lb["git_sha"] == "abc1234" and lb["n_models"] == 1
    md = bl.render_markdown(lb)
    assert "DueCare Harness-Lift Benchmark" in md
    assert "Submit a model" in md
    assert "**+50.0**" in md                      # the model's lift appears in the leaderboard row
    assert "abc1234" in md                         # provenance SHA rendered


def test_model_meta_reads_tag_size_and_documented_architecture():
    # size is read from the model tag (factual), never guessed
    assert bl.model_meta("gpt-oss:120b") == {"params": "120B", "arch": "MoE"}
    assert bl.model_meta("gemma4:31b") == {"params": "31B", "arch": "dense"}
    assert bl.model_meta("qwen3-coder:480b")["params"] == "480B"
    # MoE family whose tag carries no size -> architecture known, size "-"
    assert bl.model_meta("glm-5.2") == {"params": "-", "arch": "MoE"}
    # undisclosed architecture (proprietary preview) -> both "-"
    assert bl.model_meta("gemini-3-flash-preview") == {"params": "-", "arch": "-"}
    # every leaderboard row carries meta
    panel = _panel("gemma4:31b", 40, 90, _CB, _CF)
    rows = bl.leaderboard_rows(panel, [])
    lb = bl.build_leaderboard(panel, [], generated="2026-06-23T00:00:00Z", sha="abc1234")
    assert lb["models"][0]["meta"] == {"params": "31B", "arch": "dense"}
