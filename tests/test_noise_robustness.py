"""Noise-robustness probe: the noise transforms must be meaning-degrading-but-deterministic, and the GREP
fire-retention metric must fall to 1.0 when the 'grep' is noise-invariant and below 1.0 when it is brittle."""
from __future__ import annotations

import importlib.util
import random
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
nr = _load("noise_robustness", _ROOT / "scripts" / "noise_robustness.py")


def test_noise_transforms_are_deterministic_and_change_text():
    text = "The recruitment agency confiscated my passport and salary for the placement fee."
    for name, fn in nr.NOISE_FUNCS.items():
        a = fn(text, rate=1.0, rng=random.Random("seed"))
        b = fn(text, rate=1.0, rng=random.Random("seed"))
        assert a == b, f"{name} must be deterministic given the same seeded rng"
        assert a != text, f"{name} at rate 1.0 must change the text"


def test_misspell_uses_the_known_dictionary():
    out = nr.misspell("recruitment passport salary", rate=1.0, rng=random.Random("x"))
    assert "recruitement" in out and "pasport" in out and "salery" in out   # known misspellings applied


def test_extra_words_only_inserts_never_drops_triggers():
    text = "passport recruitment fee debt bondage"
    out = nr.insert_filler(text, rate=1.0, rng=random.Random("x"))
    for trigger in text.split():
        assert trigger in out.split()                 # insertion keeps every original (trigger) word


def test_retention_is_1_when_grep_is_noise_invariant():
    # a grep that counts a fixed keyword regardless of surrounding noise -> retention 1.0 for insertion
    def invariant_grep(text):
        return [1] if "fee" in text.lower() else []
    res = nr.measure(["the placement fee is large", "no trigger here at all"],
                     invariant_grep, levels=(0.1,))
    assert res["n_prompts_fired_clean"] == 1          # only the first prompt fires clean
    extra = [r for r in res["by_noise"] if r["noise_type"] == "extra_words"][0]
    assert extra["fire_retention"] == 1.0             # filler insertion never removes the 'fee' keyword


def test_retention_below_1_when_grep_is_spelling_brittle():
    # an EXACT-match grep for a long word that typos will corrupt -> retention < 1 under typo noise
    def brittle_grep(text):
        return [1] if "recruitment" in text.lower() else []
    res = nr.measure(["the recruitment agency took everything"] * 4, brittle_grep, levels=(0.9,))
    typo = [r for r in res["by_noise"] if r["noise_type"] == "typo"][0]
    assert typo["fire_retention"] < 1.0               # heavy typos corrupt the exact keyword -> misses


def test_expanded_bank_has_the_new_techniques():
    for t in ("drop_stopwords", "split_merge", "char_repeat", "punct_inject", "word_swap"):
        assert t in nr.NOISE_FUNCS                     # word-subtraction siblings + other techniques present


def test_drop_stopwords_only_removes_stopwords():
    text = "the recruiter took my passport for the placement fee"
    out = nr.drop_stopwords(text, rate=1.0, rng=random.Random("x"))
    assert "recruiter" in out and "passport" in out and "placement" in out and "fee" in out  # content kept
    assert "the" not in out.split() and "my" not in out.split()                              # stopwords gone


def test_punct_inject_breaks_exact_keyword():
    # a keyword-exact grep for 'passport' should MISS when the word is separator-injected ('p.a.s.s...')
    def kw(text):
        return [1] if "passport" in text.lower() else []
    res = nr.measure(["they confiscated my passport at the airport"] * 5, kw, levels=(0.9,))
    pj = [r for r in res["by_noise"] if r["noise_type"] == "punct_inject"][0]
    assert pj["fire_retention"] < 1.0                  # 'p.a.s.s...' no longer matches the exact keyword


def test_word_swap_preserves_the_word_set():
    text = "recruiter took passport placement fee"
    out = nr.word_swap(text, rate=1.0, rng=random.Random("x"))
    assert sorted(out.split()) == sorted(text.split())   # reorder only -> bag of words unchanged
