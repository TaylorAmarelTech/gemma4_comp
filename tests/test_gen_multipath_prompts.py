"""Multipath prompt generator (multi-stage chained schemes; closes the multipath 0/10 gap).

gen_multipath_prompts chains three neutral scheme mechanics across a corridor's stages (origin ->
transit -> destination) and asks the model to design the whole pipeline so no single stage looks
illegal. Deterministic, composite (no PII), regeneratable; build_benchmark_promptset folds it in as the
`multipath` source at multipath difficulty.
"""
from __future__ import annotations

import importlib.util
import json
import random
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
mp = _load("gen_multipath_prompts", _ROOT / "scripts" / "gen_multipath_prompts.py")
bp = _load("build_benchmark_promptset", _ROOT / "scripts" / "build_benchmark_promptset.py")

_PRIVATE = re.compile(r"@|\+?\d[\d ().\-]{8,}\d|\d{8,}")


def test_full_product_all_unique():
    rows = mp.generate()
    assert len(rows) == len(mp.ALL_CORRIDORS) * len(mp.CHAINS) * len(mp.FRAMINGS) == 176
    assert len({r["id"] for r in rows}) == len(rows)
    assert len({r["text"] for r in rows}) == len(rows)


def test_fields_difficulty_and_no_pii():
    for r in mp.generate():
        assert r["id"].startswith("MULTIPATH-")
        assert r["difficulty"] == "multipath"
        assert r["category"].startswith("multipath_")
        assert r["framing"] in {f[0] for f in mp.FRAMINGS}
        assert r["source"] == "multipath"
        assert "->" in r["corridor"]
        # a multipath prompt chains THREE stages -- the stage cues appear
        assert "recruitment" in r["text"].lower() or "at origin" in r["text"].lower()
        assert "destination" in r["text"].lower()
        assert len(r["text"]) > 300                           # substantial 3-stage chains
        assert not _PRIVATE.search(r["text"])


def test_deterministic_and_committed_matches():
    assert mp.generate() == mp.generate()
    committed = [json.loads(l) for l in mp.OUT_DEFAULT.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert committed == mp.generate()


def test_build_folds_multipath_source():
    rows = bp._stratified(bp._load_jsonl(bp.MULTIPATH), "multipath", 3, set(), set(), random.Random(0))
    assert rows and all(r["source"] == "multipath" for r in rows)
    assert all(r["difficulty"] == "multipath" for r in rows)
    doc = bp.build(per_category_expansion=1, per_category_majorcase=1, per_category_pretext=1,
                   per_category_multipath=2, per_category_seed=1, per_category_hermes=1,
                   max_prompt_chars=6000)
    assert doc["_build"]["multipath"] > 0
    assert "multipath" in {p["source"] for p in doc["prompts"]}
