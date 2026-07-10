"""GREP fire-rate coverage over multilingual/slang variants (reproducible non-English detection metric)."""
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
gc = _load("grep_multilingual_coverage", _ROOT / "scripts" / "grep_multilingual_coverage.py")


def _fake_grep(keywords):
    """A grep_call stand-in: fires one 'rule' per English keyword present as a WORD in the text (so a
    pure translation that drops the English keywords fires fewer -- exactly the real behaviour). Word-
    boundary matching avoids accidental substring hits."""
    def grep_call(text):
        words = set((text or "").lower().replace(",", " ").replace(".", " ").split())
        return {"hits": [k for k in keywords if k in words]}
    return grep_call


def test_coverage_reports_fire_ratio_per_language_and_variant():
    # english source has 3 trigger keywords; code_switch keeps them, full_translation drops them
    items = [
        {"source_id": "s1", "source_text_en": "recruitment fee invoice cap",
         "language": "Bengali", "variant_kind": "code_switched", "text": "ami recruitment fee invoice cap niye"},
        {"source_id": "s1", "source_text_en": "recruitment fee invoice cap",
         "language": "Bengali", "variant_kind": "full_translation", "text": "purely bengali script no english"},
    ]
    cov = gc.coverage(items, _fake_grep(["recruitment", "invoice", "cap"]))
    assert cov["english_mean_fired"] == 3.0                 # the source fires all 3
    by = {(r["language"], r["variant_kind"]): r for r in cov["by_group"]}
    cs = by[("Bengali", "code_switched")]
    ft = by[("Bengali", "full_translation")]
    assert cs["mean_fired"] == 3.0 and cs["fire_ratio_vs_english"] == 1.0   # code-switch keeps triggers
    assert ft["mean_fired"] == 0.0 and ft["fire_ratio_vs_english"] == 0.0   # pure translation loses them


def test_n_fired_is_defensive():
    def boom(_text):
        raise RuntimeError("bad rule")
    assert gc.n_fired(boom, "x") == 0                       # a crashing grep never breaks the sweep
    assert gc.n_fired(lambda t: {"hits": [1, 2]}, "x") == 2
