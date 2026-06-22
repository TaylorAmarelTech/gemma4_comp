"""Tests for scripts/gen_scheme_prompts.py -- deterministic adversarial scheme-prompt generation."""
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


gen = _load("gen_scheme_prompts", _ROOT / "scripts" / "gen_scheme_prompts.py")


def test_generate_count_unique_and_format():
    ps = gen.generate(70)
    assert len(ps) == 70
    assert len({p["id"] for p in ps}) == 70          # unique ids
    assert len({p["text"] for p in ps}) == 70        # unique texts (no saturation)
    for p in ps:
        assert set(p) >= {"id", "text", "category", "difficulty", "corridor"}
        assert p["id"].startswith("SCHEME-") and p["difficulty"] == "hard"
        assert "->" in p["corridor"]


def test_all_schemes_represented_and_balanced():
    ps = gen.generate(140)                            # 20 per scheme target
    by = {}
    for p in ps:
        by[p["category"]] = by.get(p["category"], 0) + 1
    assert set(by) == {s[0] for s in gen.SCHEMES}     # every scheme appears
    assert min(by.values()) >= 10                     # none starved


def test_deterministic_no_random():
    a = [p["id"] for p in gen.generate(50)]
    b = [p["id"] for p in gen.generate(50)]
    assert a == b                                     # stable across runs (content-hash ids)


def test_prompts_are_grounded_and_adversarial():
    ps = gen.generate(70)
    blob = " ".join(p["text"] for p in ps)
    # grounded in real statutes/corridors, framed as scheme-design asks
    assert "Emigration Act 1983" in blob or "Foreign Employment Act" in blob
    assert "recruitment fee" in blob.lower() or "fee" in blob.lower()
    # composite agencies only (no obviously-real org); each agency is from the synthetic list
    assert any(a in blob for a in gen.AGENCIES)
