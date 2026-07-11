"""Multilingual + synonym indicator lexicon: the paraphrase and non-English reports that used to match
NOTHING (adversarial audit items 1 & 2) now fire the right ILO indicators, without spurious benign hits."""
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
lex = _load("indicator_lexicon", _ROOT / "scripts" / "indicator_lexicon.py")
lr = _load("legal_reasoning", _ROOT / "scripts" / "legal_reasoning.py")


def test_paraphrase_attack_now_fires():
    # the exact adversarial paraphrase the audit verified matched NOTHING before this lexicon
    inds = lr.match_indicators("The office is keeping my travel booklet and I have a cash advance I must "
                               "earn back before they let me go. They are holding my pay and I get no day off.")
    assert "retention of identity documents" in inds     # 'travel booklet'
    assert "debt bondage" in inds                          # 'cash advance' / 'earn back'
    assert "restriction of movement" in inds               # 'let me go'
    assert "withholding of wages" in inds                  # 'holding my pay'


def test_non_english_report_fires():
    # Tagalog: "they took my passport and I can't leave" -- fired nothing before
    inds = lr.match_indicators("Kinuha nila ang aking pasaporte at hindi ako makaalis.")
    assert "retention of identity documents" in inds       # 'pasaporte' / 'kinuha ang aking pasaporte'
    assert "restriction of movement" in inds               # 'hindi ako makaalis'


def test_lexicon_exposes_terms_and_coverage():
    assert "pasaporte" in lex.terms_for("retention of identity documents")
    assert any("cash advance" == t for t in lex.terms_for("debt bondage"))
    cov = lex.coverage()
    assert cov["debt bondage"]["synonym_en"] > 0 and cov["retention of identity documents"]["multilingual"] > 0


def test_benign_text_not_spuriously_fired():
    inds = lr.match_indicators("I love my job and my employer pays me on time every month; it is a good place.")
    assert "debt bondage" not in inds
    assert "retention of identity documents" not in inds
    assert "restriction of movement" not in inds
