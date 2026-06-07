"""Tests for cross-domain word-sense disambiguation (the second representation
bottleneck: meaning collapsed into ambiguous tokens) and its relevance gate."""
from __future__ import annotations

from duecare.research_tools.ambiguity import domain_sense, is_offdomain
from duecare.research_tools.relevance import relevance_with_domain_sense


def _term(report, name):
    return next((t for t in report["terms"] if t["term"] == name), None)


def test_bond_debt_bondage_sense_is_target():
    r = domain_sense("The worker had to post a bond to the recruiter and repay it from wages.")
    bond = _term(r, "bond")
    assert bond is not None and bond["dominant"] == "target"
    assert r["collision"] is False and r["net"] >= 1


def test_bond_finance_sense_is_offdomain_collision():
    r = domain_sense("The 10-year Treasury bond yield rose as investors weighed maturity and coupon.")
    bond = _term(r, "bond")
    assert bond["dominant"] == "offdomain" and bond["offdomain_label"] == "finance"
    assert bond["target_hits"] == 0
    assert r["collision"] is True and "finance" in r["offdomain_labels"]


def test_trafficking_human_sense_is_target():
    r = domain_sense("Human trafficking of migrant workers for forced labour was documented.")
    tk = _term(r, "traffick")
    assert tk is not None and tk["dominant"] == "target" and r["collision"] is False


def test_trafficking_data_network_sense_is_collision():
    r = domain_sense("Network trafficking consumed bandwidth across the data link as packets dropped.")
    tk = _term(r, "traffick")
    assert tk["dominant"] == "offdomain" and tk["offdomain_label"] == "data_network"
    assert r["collision"] is True


def test_charge_electrical_vs_fee():
    elec = domain_sense("The battery charge dropped to 20% as the voltage fell.")
    assert _term(elec, "charge")["offdomain_label"] == "electrical" and elec["collision"] is True
    fee = domain_sense("The recruiter will charge the worker a placement fee deducted from wages.")
    assert _term(fee, "charge")["dominant"] == "target" and fee["collision"] is False


def test_bare_ambiguous_term_is_unresolved_not_collision():
    # term present, no anchors either way -> genuinely ambiguous, but NOT a collision
    r = domain_sense("He signed for the bond.")
    assert _term(r, "bond")["dominant"] == "unresolved"
    assert r["n_unresolved"] == 1 and r["collision"] is False


def test_clean_trafficking_text_has_no_collision_terms():
    r = domain_sense("Recruitment fees may not be collected from the migrant worker under ILO C189.")
    assert r["terms"] == [] and r["collision"] is False and r["net"] == 0


def test_is_offdomain_convenience():
    assert is_offdomain("Corporate bond spreads widened versus the issuer's portfolio.") is True
    assert is_offdomain("Debt bondage: the worker repays a recruitment bond from withheld wages.") is False


# --- the acquisition gate wrapper -------------------------------------------------

def test_gate_flags_and_demotes_offdomain_family_false_positive():
    # "freedom of movement" hits the restricted_movement lexicon family (-> medium),
    # but the page is about capital markets: the bond keyword resolves to finance.
    text = ("Freedom of movement of capital underpins the bond market, where yields "
            "and investors set the issuer's cost.")
    out = relevance_with_domain_sense(text)
    assert out["review_flag"] is True
    assert out["demoted_for_collision"] is True and out["tier"] == "low"


def test_gate_keeps_genuine_trafficking_chunk_and_does_not_flag():
    # bare collision terms used in their TARGET sense: agent (recruitment agent),
    # charge (charge ... a fee), bond (repay the bond from wages).
    text = ("The recruitment agent will charge the migrant worker a placement fee, then "
            "make her repay the bond from withheld wages while her passport is retained.")
    out = relevance_with_domain_sense(text)
    assert out["review_flag"] is False and out["demoted_for_collision"] is False
    assert out["tier"] in ("medium", "high")
    assert out["domain_sense"]["net"] >= 1
    # all three ambiguous terms resolve to the trafficking sense
    assert out["domain_sense"]["n_offdomain"] == 0
