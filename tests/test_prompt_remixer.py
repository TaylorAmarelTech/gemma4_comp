"""Tests for the deterministic prompt remixer (anti-benchmark-maxing)."""
from __future__ import annotations

import importlib
import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SCRIPTS = _ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

rx = importlib.import_module("prompt_remixer")


def _bases(n):
    return [{"id": f"B{i}", "text": f"worker scenario number {i} with a fee question?",
             "category": "x", "framing": "worker_query"} for i in range(n)]


def test_remix_records_provenance_and_all_transforms():
    out = rx.remix(_bases(6))
    transforms = {v["transform"] for v in out}
    assert {"pad_buried", "persona_shift", "punctuate", "combine",
            "typo", "contraction", "leet"} <= transforms
    for v in out:
        assert v["id"].startswith("RMX-")
        assert v["base_ids"]                      # provenance recorded
        assert v["category"] == f"remix_{v['transform']}"
        if v["transform"] == "combine":
            assert len(v["base_ids"]) == 2        # composed from two bases


def test_remix_is_deterministic():
    a = rx.remix(_bases(8))
    b = rx.remix(_bases(8))
    assert [v["id"] for v in a] == [v["id"] for v in b]


def test_heldout_split_is_disjoint():
    bases = _bases(20)
    seen, held = rx.split_bases(bases, held_out_every=5)
    seen_ids = {b["id"] for b in seen}
    held_ids = {b["id"] for b in held}
    assert seen_ids.isdisjoint(held_ids)
    assert len(seen) + len(held) == 20
    assert len(held) == 4                          # every 5th of 20


def test_punctuate_changes_text():
    base = "this is a normal sentence about wages and fees."
    assert any(rx._punctuate(base, i) != base for i in range(4))


def test_surface_transforms_meaning_preserving_and_deterministic():
    base = "the recruitment agency will not return the worker passport without a fee"
    nwords = len(base.split())
    t = rx._typo(base, 3)
    assert t != base and len(t.split()) == nwords          # perturbs chars, not word count
    assert rx._typo(base, 3) == t                          # deterministic
    assert rx._leet(base, 1) != base and rx._leet(base, 1) == rx._leet(base, 1)
    assert rx._contraction("the agency will not return it", 0) == "the agency won't return it"
    # short / empty text never crashes (no eligible words -> unchanged)
    assert rx._typo("hi", 0) == "hi" and rx._leet("", 0) == ""


def test_spintax_expand_deterministic_and_enumerates():
    t = "I am {an investigator|a researcher} asking about a {fee|loan}."
    a, b = rx._spintax_expand(t, 0), rx._spintax_expand(t, 1)
    assert "{" not in a                          # fully expanded
    assert a == rx._spintax_expand(t, 0)         # deterministic
    assert a != b                                # different seed -> different combo
    assert len({rx._spintax_expand(t, s) for s in range(4)}) == 4   # full 2x2 cross-product


def test_spintax_variants_are_expanded_combined_attack():
    v = rx.spintax_variants(per_template=5)
    assert v
    assert all(x["category"] == "combined_attack" and x["transform"] == "spintax" for x in v)
    assert all("{" not in x["text"] for x in v)  # no unexpanded templates leak through
    assert all(x["id"].startswith("RMX-") for x in v)
