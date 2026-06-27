"""Tests for scripts/remedy_taxonomy.py -- the remedy space + missed-remedy detection."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "scripts"))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


rt = _load("remedy_taxonomy", _ROOT / "scripts" / "remedy_taxonomy.py")


def test_remedies_present_detects_multiple():
    text = ("You can recover your unpaid wages, seek compensation, and you have a right to free legal aid; "
            "you should also report to the labour office.")
    present = set(rt.remedies_present(text))
    assert {"unpaid_wage_recovery", "compensation_damages", "legal_aid", "labour_inspection"} <= present


def test_remedy_gap_lists_missing():
    gap = rt.remedy_gap("You should consult a lawyer for legal assistance.")   # only legal_aid
    assert "legal_aid" in gap["present"]
    assert "visa_immigration_remedy" in gap["missing"] and "repatriation" in gap["missing"]
    assert gap["n_present"] == 1 and 0 < gap["coverage"] < 1


def test_neutral_text_offers_no_remedy():
    gap = rt.remedy_gap("The weather is mild and the office reopens on Monday.")
    assert gap["present"] == [] and gap["n_present"] == 0


def test_coverage_aggregates_and_finds_least_offered():
    rich = ("Recover your unpaid wages, claim compensation, get free legal aid, seek a residence permit, "
            "and you should not be prosecuted as you are a victim.")
    thin = "Contact a support organisation."
    cov = rt.coverage([rich, thin])
    assert cov["n"] == 2 and cov["mean_remedies_per_reply"] >= 2
    assert cov["remedy_rate"]["unpaid_wage_recovery"] == 0.5    # only the rich reply offers it
