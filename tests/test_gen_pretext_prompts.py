"""Pretext-framing prompt generator (the measured third-party-wrapper framing gap).

gen_pretext_prompts wraps neutral third-person scheme mechanics (reusing gen_scheme_prompts' vetted
corridors + statutes) in distinct pretext voices (journalist / trainer / consultant / academic /
policy / software-founder / buried-benign), each asking for the operational playbook under a cover
story. Deterministic, composite (no PII), propose-only. build_benchmark_promptset folds it in as the
`pretext` source, preserving the `framing` field for the framing-gap analysis.
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
gp = _load("gen_pretext_prompts", _ROOT / "scripts" / "gen_pretext_prompts.py")
bp = _load("build_benchmark_promptset", _ROOT / "scripts" / "build_benchmark_promptset.py")

_EMAIL_OR_PHONE = re.compile(r"@|\+?\d[\d ().\-]{8,}\d")


def test_generate_produces_full_product_all_unique():
    rows = gp.generate()
    expected = len(gp.ALL_CORRIDORS) * len(gp.SCHEMES) * len(gp.FRAMINGS)
    assert len(rows) == expected == 1848
    assert len({r["id"] for r in rows}) == len(rows)          # unique ids
    assert len({r["text"] for r in rows}) == len(rows)        # unique texts
    assert len(gp.ALL_CORRIDORS) == 22 and len(gp.SCHEMES) == 12 and len(gp.FRAMINGS) == 7


def test_every_prompt_has_required_fields_and_no_pii():
    for r in gp.generate():
        assert r["id"].startswith("PRETEXT-")
        assert r["category"].startswith("pretext_")
        assert r["framing"] in {f[0] for f in gp.FRAMINGS}
        assert r["difficulty"] in ("hard", "very_hard")
        assert r["source"] == "pretext"
        assert "->" in r["corridor"]
        assert len(r["text"]) > 120
        assert not _EMAIL_OR_PHONE.search(r["text"])          # composite only, no contact details


def test_difficulty_follows_framing_subtlety():
    by_framing = {r["framing"]: r["difficulty"] for r in gp.generate()}
    # cover-story framings that could pass as legitimate curiosity are very_hard
    assert by_framing["journalist"] == "very_hard"
    assert by_framing["software_founder"] == "very_hard"
    assert by_framing["buried_benign_preamble"] == "very_hard"
    # framings that overtly signal an operational request are hard
    assert by_framing["compliance_trainer"] == "hard"
    assert by_framing["policy_analyst"] == "hard"


def test_generation_is_deterministic():
    assert gp.generate() == gp.generate()


def test_committed_file_matches_generator():
    committed = [json.loads(l) for l in gp.OUT_DEFAULT.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert committed == gp.generate()                         # the committed jsonl is regeneratable


def test_prompts_reference_the_corridor_statute_not_invented_law():
    # each mechanic embeds the corridor's real statute/dest-law; spot-check a known corridor
    rows = gp.generate()
    ph_hk = [r for r in rows if r["corridor"] == "Philippines->Hong Kong"]
    assert ph_hk
    assert any("RA 8042" in r["text"] for r in ph_hk)         # the vetted origin statute appears


# ---- build_benchmark_promptset integration --------------------------------------------------------

def test_build_folds_pretext_source_preserving_framing():
    rows = bp._stratified(bp._load_jsonl(bp.PRETEXT), "pretext", 3,
                          set(), set(), random.Random(0))
    assert rows and all(r["source"] == "pretext" for r in rows)
    assert all("framing" in r for r in rows)                  # framing survives _norm for the pretext source
    # a non-pretext row keeps no framing key
    normed = bp._norm({"id": "X", "text": "t", "category": "c"}, "scheme")
    assert "framing" not in normed


def test_build_includes_pretext_in_the_board():
    doc = bp.build(per_category_expansion=1, per_category_majorcase=1, per_category_pretext=2,
                   per_category_seed=1, per_category_hermes=1, max_prompt_chars=6000)
    assert doc["version"] == "1.4"
    assert doc["_build"]["pretext"] > 0
    sources = {p["source"] for p in doc["prompts"]}
    assert "pretext" in sources
    # scheme core is still first and contiguous (resumable by prompt_id)
    scheme_ct = doc["_build"]["scheme"]
    assert all(doc["prompts"][i]["source"] == "scheme" for i in range(scheme_ct))
