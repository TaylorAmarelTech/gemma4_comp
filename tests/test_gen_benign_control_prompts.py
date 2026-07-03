"""Benign control set generator (over-refusal split, roadmap P5).

gen_benign_control_prompts templates ~20 legitimate worker-help topics across the 22 vetted corridors
into a stratified benign control set (grown from the 16-prompt hand-authored seed). Deterministic,
composite (no PII / no volatile facts), and it must pass rich_harness_lift's fail-closed loader
(unique ids, all intent=benign, non-blank, no private hints, top-level intent "benign_control").
"""
from __future__ import annotations

import importlib.util
import json
import re
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
for _src in _ROOT.glob("packages/*/src"):
    sys.path.insert(0, str(_src))
gb = _load("gen_benign_control_prompts", _ROOT / "scripts" / "gen_benign_control_prompts.py")
rh = _load("rich_harness_lift", _ROOT / "scripts" / "rich_harness_lift.py")

_PRIVATE_HINT = re.compile(r"@|\+?\d[\d ().\-]{8,}\d|\d{8,}")


def test_generate_full_product_all_unique():
    rows = gb.generate()
    # every topic references both origin and destination, so the full corridor x topic product is unique
    assert len(rows) == len(gb.ALL_CORRIDORS) * len(gb._topics("O", "D")) == 440  # 22 x 20, no dedup drops
    assert len({r["id"] for r in rows}) == len(rows)          # unique ids
    assert len({r["text"] for r in rows}) == len(rows)        # unique texts


def test_every_prompt_is_benign_and_clean():
    for r in gb.generate():
        assert r["id"].startswith("BENIGN-")
        assert r["intent"] == "benign"
        assert r["difficulty"] == "benign"
        assert r["source"] == "benign_control_synthetic"
        assert "->" in r["corridor"]
        assert len(r["text"]) > 60
        assert not _PRIVATE_HINT.search(r["text"])            # no contact details / long digit runs


def test_generation_is_deterministic():
    assert gb.generate() == gb.generate()


def test_committed_set_matches_generator_and_grew():
    path = gb.OUT_DEFAULT
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert doc["intent"] == "benign_control"
    assert doc["prompts"] == gb.generate()                    # committed file is regeneratable
    assert len(doc["prompts"]) >= 400                         # grown well past the 16-prompt seed


def test_committed_set_passes_the_fail_closed_loader():
    # the loader raises on PII / dup ids / non-benign / blank; a clean generated set must load
    loaded = rh.load_benign_control_prompts(gb.OUT_DEFAULT)
    assert len(loaded) == len(gb.generate())
    assert all(p["intent"] == "benign" for p in loaded)
