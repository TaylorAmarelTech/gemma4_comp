"""Tests for scripts/frontier_report.py -- the report builder + model routing.

Offline: the report aggregation / example-card selection / markdown rendering and the
Ollama-vs-OpenRouter routing are pure, so no network or API key is needed.
"""
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


fr = _load("frontier_report", _ROOT / "scripts" / "frontier_report.py")

_SYNTH = [
    {"model": "m1", "prompt_id": "p1", "prompt_text": "WORKER MESSAGE ONE",
     "arm": "baseline", "response": "BASELINE BAD REPLY", "score": 3.0},
    {"model": "m1", "prompt_id": "p1", "prompt_text": "WORKER MESSAGE ONE",
     "arm": "harnessed", "response": "HARNESSED GOOD REPLY", "score": 8.0},
    {"model": "m2", "prompt_id": "p1", "prompt_text": "WORKER MESSAGE ONE",
     "arm": "baseline", "response": "ok reply", "score": 6.0},
    {"model": "m2", "prompt_id": "p1", "prompt_text": "WORKER MESSAGE ONE",
     "arm": "harnessed", "response": "slightly better", "score": 7.0},
]


def test_aggregate_computes_and_sorts_lift():
    rows = fr._aggregate(_SYNTH)
    by = {r["model"]: r for r in rows}
    assert by["m1"]["lift"] == 5.0 and by["m2"]["lift"] == 1.0
    assert rows[0]["model"] == "m1"          # sorted by lift descending


def test_example_cards_pick_biggest_improvement_first():
    cards = fr._example_cards(_SYNTH)
    assert cards[0]["model"] == "m1" and cards[0]["gap"] == 5.0
    # an arm-incomplete pair contributes no card
    assert fr._example_cards(_SYNTH[:1]) == []


def test_build_report_renders_table_and_full_text_cards(tmp_path):
    p = tmp_path / "r.md"
    md = fr.build_report(_SYNTH, judge="gpt-oss:120b", path=p)
    assert "Per-model lift" in md and "| `m1` |" in md
    assert "poor baseline" in md.lower()
    # full text, not truncated: prompt + BOTH arm responses appear verbatim
    assert "WORKER MESSAGE ONE" in md
    assert "BASELINE BAD REPLY" in md and "HARNESSED GOOD REPLY" in md
    assert "+5.00" in md                     # m1's lift in the table
    assert p.exists()


def test_model_routing_ollama_vs_openrouter():
    assert fr._is_openrouter("openai/gpt-4o")
    assert fr._is_openrouter("openrouter:anthropic/claude-3.7-sonnet")
    assert not fr._is_openrouter("glm-5.2")
    assert not fr._is_openrouter("ollama:gemma4:31b")   # explicit ollama: prefix stays Ollama
