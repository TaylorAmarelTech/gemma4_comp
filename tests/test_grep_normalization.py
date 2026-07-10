"""Pre-GREP normaliser prototype: 'none' must be the untouched original, the normalisers must fix
elongation/separator evasion, and the eval must report recall AND precision with 'none' as the baseline."""
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
gn = _load("grep_normalization", _ROOT / "scripts" / "grep_normalization.py")


def test_none_is_the_untouched_original():
    text = "p.a.s.s.p.o.r.t pleaseee help"
    assert gn.normalize_for_grep(text, "none") == text          # the original method is preserved verbatim


def test_collapse_repeats_fixes_elongation():
    assert gn.normalize_for_grep("pleaseee help meee", "collapse_repeats") == "please help me"
    # a 2-char double is NOT collapsed (only 3+), so real words survive
    assert gn.normalize_for_grep("passport fee", "collapse_repeats") == "passport fee"


def test_strip_separators_fixes_evasion_without_touching_word_gaps():
    assert gn.normalize_for_grep("p.a.s.s.p.o.r.t", "strip_separators") == "passport"
    assert gn.normalize_for_grep("recruit-ment", "strip_separators") == "recruitment"
    # separators between real WORDS (space) are untouched; only intra-token . - * go
    assert gn.normalize_for_grep("took my passport today", "strip_separators") == "took my passport today"


def test_both_applies_both():
    assert gn.normalize_for_grep("p.a.s.s.p.o.r.t pleaseee", "both") == "passport please"


def test_eval_keeps_none_baseline_and_reports_recall_and_precision():
    # a keyword grep for 'passport' -- exact match, so evasion breaks it and normalisation should restore it
    def kw(text):
        return [1] if "passport" in text.lower() else []
    res = gn.evaluate(["they confiscated my passport at the airport"] * 5, kw, levels=(0.2,))
    assert res["strengths"][0] == "none"                        # original method is the first/baseline column
    assert {"recall", "precision"} <= set(res)                  # both halves reported
    pj = {r["strength"]: r["retention"] for r in res["recall"]
          if r["noise"] == "punct_inject" and r["level"] == 0.2}
    assert pj["both"] >= pj["none"]                            # normalisation never HURTS evasion recall here
    # (direct restoration p.a.s.s.p.o.r.t -> passport is asserted in test_strip_separators; punct_inject
    #  also uses SPACE as a separator, which the normaliser intentionally does not rejoin, so >= not >)
    # precision: the benign off_topic set must not fire under ANY strength (no false positives introduced)
    off = {r["strength"]: r["mean_fired"] for r in res["precision"] if r["set"] == "off_topic"}
    assert off["both"] == off["none"] == 0.0                    # normalisation invents no off-topic matches
