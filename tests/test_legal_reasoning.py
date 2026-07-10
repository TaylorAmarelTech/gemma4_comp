"""Deterministic legal-reasoning engine: indicators, applicable-claim selection (jurisdiction + topic),
Palermo element analysis, freshness recheck flags, and the never-a-criminal-finding disclaimer."""
from __future__ import annotations

import importlib.util
import sys
from datetime import date
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


sys.path.insert(0, str(_ROOT / "scripts"))
lr = _load("legal_reasoning", _ROOT / "scripts" / "legal_reasoning.py")


def test_match_indicators_from_worker_perspective():
    inds = lr.match_indicators("They took my passport and I must repay a placement fee; I cannot leave the house")
    assert "retention of identity documents" in inds
    assert "debt bondage" in inds
    assert "restriction of movement" in inds                    # "cannot leave" is the explicit movement signal


def test_applicable_claims_respect_jurisdiction_and_topic():
    claims = lr.load_claims()
    sc = {"id": "s", "jurisdiction": "PH", "destination": "HK",
          "facts": ["charged a placement fee", "took my passport"]}
    ids = {c["id"]: c for c in lr.applicable_claims(sc, claims, date(2026, 7, 10))}
    assert "ph_placement_fee" in ids                            # PH fee rule applies (matches jurisdiction+topic)
    assert "c181_recruitment_fees" in ids                       # international fee standard always relevant
    assert "hk_money_lending_cap" not in ids                    # no loan/interest fact -> not pulled in
    assert ids["ph_placement_fee"]["recheck"] is True          # PH fee is high-volatility -> recheck flagged


def test_palermo_all_three_elements_gives_risk_pattern_not_finding():
    inds = lr.match_indicators("recruitment agency took my passport, debt to repay, wages withheld, 18 hours no rest day")
    el = lr.palermo_elements(inds, {"facts": ["a recruitment agency ..."]})
    assert el["act"]["supported"] and el["means"]["supported"] and el["purpose"]["supported"]
    assert "NOT a criminal finding" in el["reading"] and "CHILD" in el["reading"]


def test_analyze_flags_volatile_claims_and_never_asserts_a_finding():
    claims = lr.load_claims()
    a = lr.analyze(lr.SCENARIOS[0], claims, date(2026, 7, 10))
    assert "ph_placement_fee" in a["uncertainty_recheck"]       # the volatile PH rule is surfaced for verification
    assert "not a criminal determination" in a["_disclaimer"]
    assert any("SAFETY" in w for w in a["public_interest_worker_protective"])


def test_us_scenario_pulls_the_current_tvpa_standard_not_kozminski_as_current():
    claims = lr.load_claims()
    a = lr.analyze(lr.SCENARIOS[3], claims, date(2026, 7, 10))   # US psychological-coercion scenario
    by_id = {c["id"]: c for c in a["applicable_claims"]}
    assert "us_tvpa_1589" in by_id                              # the current US forced-labour standard is surfaced
    assert by_id["us_tvpa_1589"]["status"] == "current"
    # build-upon/supersede is ENFORCED, not just recorded: if the superseded kozminski case is surfaced at all,
    # it must be labelled historical (never as an equal current standard), and it must sort AFTER the successor.
    if "kozminski_1988" in by_id:
        assert by_id["kozminski_1988"]["status"] == "historical"
        assert "superseded" in by_id["kozminski_1988"]["binding_here"]
        order = [c["id"] for c in a["applicable_claims"]]
        assert order.index("us_tvpa_1589") < order.index("kozminski_1988")


def test_keyword_matching_uses_word_boundaries_not_substrings():
    # substring containment silently fired ordinary English: "feel"->"fee", "however"->"owe", "white"->"hit".
    # whole-word matching must NOT raise those indicators/claims from innocuous words.
    assert "debt bondage" not in lr.match_indicators("The schedule is flexible; however, I get one day off.")
    assert "physical or sexual violence" not in lr.match_indicators("They drive us in a white van every day.")
    claims = lr.load_claims()
    sc = {"id": "s", "jurisdiction": "US", "destination": "US",
          "facts": ["There is no physical restraint but I feel I cannot leave."]}
    ids = {c["id"] for c in lr.applicable_claims(sc, claims, date(2026, 7, 10))}
    assert "c181_recruitment_fees" not in ids                   # "feel" must NOT trip the recruitment-fee claim
    assert "ph_placement_fee" not in ids
    # the genuine whole-word signals still fire
    assert "debt bondage" in lr.match_indicators("I owe a large debt and must repay it.")
    assert "intimidation and threats" in lr.match_indicators("My boss threatens and threatened me repeatedly.")
