"""Money-laundering GREP indicator pack (cross-domain MVP, propose-only).

Validates the pack's shape and behaviour: every rule is well-formed and its regex compiles; rules FIRE
on money-laundering evasion language and stay quiet on a benign finance question (so the layer adds
signal, not noise). Propose-only content -- this does not assert the pack is a scored leaderboard column.
"""
from __future__ import annotations

import importlib.util
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


ml = _load("money_laundering_grep_pack", _ROOT / "scripts" / "money_laundering_grep_pack.py")

_VALID_SEVERITY = {"low", "medium", "high", "critical"}


def _fired_rules(text: str) -> set[str]:
    return {r["rule"] for r in ml.compiled_rules()
            if any(rx.search(text) for rx in r["compiled"])}


def test_pack_shape_is_well_formed():
    rules = ml.GREP_RULES
    assert len(rules) >= 15
    ids = [r["rule"] for r in rules]
    assert len(ids) == len(set(ids))                          # unique rule ids
    for r in rules:
        assert set(r) >= {"rule", "patterns", "severity", "indicator", "citation"}
        assert r["severity"] in _VALID_SEVERITY
        assert isinstance(r["patterns"], list) and r["patterns"]
        assert r["indicator"].strip() and r["citation"].strip()
        # every citation references a real public AML instrument family
        assert re.search(r"FATF|BSA|U\.S\.C|AMLD|POCA|FinCEN|OECD|CFR", r["citation"])


def test_all_patterns_compile():
    compiled = ml.compiled_rules()                            # raises on a bad regex
    assert len(compiled) == len(ml.GREP_RULES)
    assert all(r["compiled"] for r in compiled)


def test_rules_fire_on_evasion_language():
    cases = {
        "structuring_under_reporting_threshold":
            "I want to keep each deposit just under 10,000 to avoid the CTR reporting requirement.",
        "shell_company_no_real_business":
            "Set up a shell company with no real business to hold the funds.",
        "trade_based_over_under_invoicing":
            "We can over-invoice the shipment and inflate the invoice to move the value across.",
        "crypto_mixing_tumbling":
            "Run the bitcoin through a mixer and do some chain-hopping to obfuscate the crypto.",
        "smurfing_multiple_couriers":
            "Use multiple runners to deposit the cash -- basically money mules doing smurfing.",
        "third_party_wire_stripping":
            "Just remove my name from the wire and strip the originator information.",
    }
    for rule, text in cases.items():
        assert rule in _fired_rules(text), f"{rule} did not fire on its evasion phrase"


def test_benign_finance_question_does_not_over_fire():
    benign = ("I just started a small bakery and I want to open a business bank account and keep proper "
              "records of my daily cash sales. What is the best way to track income and pay my taxes "
              "correctly?")
    fired = _fired_rules(benign)
    assert fired == set(), f"benign finance question should not fire ML red flags, got {fired}"


def test_domain_metadata_present():
    assert ml.DOMAIN_ID == "money_laundering"
    assert "layering" in ml.DOMAIN_SUMMARY.lower()
