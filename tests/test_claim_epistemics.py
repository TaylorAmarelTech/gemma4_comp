"""Claim epistemics: separate law from rumour / faith-framing / control-narrative / misunderstanding, and
return the right verification posture + a myth->reality catalog anchored to the legal-claim library."""
from __future__ import annotations

import importlib.util
import json
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
ce = _load("claim_epistemics", _ROOT / "scripts" / "claim_epistemics.py")


def test_core_statuses_classify():
    assert ce.classify_epistemic_status("Your passport belongs to the company.")["status"] == "control_narrative"
    assert ce.classify_epistemic_status("It's haram to leave your job.")["status"] == "faith_or_moral_framing"
    assert ce.classify_epistemic_status("Everyone says you can't complain.")["status"] == "folk_belief_or_rumor"
    assert ce.classify_epistemic_status("Kafala means you can never change jobs.")["status"] == "misunderstanding"
    assert ce.classify_epistemic_status("Under Article 6 of Convention No. 97, equal treatment applies."
                                        )["status"] == "law"
    assert ce.classify_epistemic_status("The ILO fair recruitment principles say the employer pays."
                                        )["status"] == "official_guidance"
    assert ce.classify_epistemic_status("The weather is nice today.")["status"] == "unclear"


def test_debt_before_leave_is_a_control_narrative():
    # the fixed case: 'placement' between 'your' and 'debt', and 'let you leave' as the exit
    assert ce.classify_epistemic_status("You must work off your placement debt before they let you leave."
                                        )["status"] == "control_narrative"
    # a benign repayment obligation (no exit coercion) is NOT a control narrative
    assert ce.classify_epistemic_status("You must repay your loan before the end of the year."
                                        )["status"] != "control_narrative"


def test_beneficiary_lawwashing_is_still_a_control_narrative():
    # a rule that name-drops 'the law' but is asserted by the party who benefits and traps the worker
    said_by_employer = ce.classify_epistemic_status(
        "Under the labour law, you must stay until the contract ends.", attributed_to="employer")
    assert said_by_employer["status"] == "control_narrative"
    # the SAME sentence with no beneficiary attribution reads as a (verifiable) legal claim, not coercion
    neutral = ce.classify_epistemic_status("Under the labour law, you must stay until the contract ends.")
    assert neutral["status"] == "law"


def test_posture_flags_verification_and_counter():
    for status in ("folk_belief_or_rumor", "faith_or_moral_framing", "control_narrative",
                   "misunderstanding", "unclear"):
        assert status in ce._NEEDS_VERIFICATION
    # law / guidance / verified fact do NOT need the 'not established law' flag
    assert ce.classify_epistemic_status("Under Section 1591, ...")["needs_verification"] is False
    # only the abuser-substitutes-for-law statuses trigger an active COUNTER
    assert ce.classify_epistemic_status("Your passport belongs to the agency.")["should_counter"] is True
    assert ce.classify_epistemic_status("Everyone says you can't complain.")["should_counter"] is False


def test_assess_surfaces_myth_reality_and_a_real_corpus_anchor():
    a = ce.assess("The company owns your passport.", attributed_to="employer")
    assert a["status"] == "control_narrative" and a["should_counter"] is True
    assert a["catalog_match"] is not None and "passport" in a["catalog_match"]["reality"].lower()
    # every anchor in the catalog must resolve to a real claim id in the live legal-claim library
    ids = {c["id"] for c in json.loads(
        (_ROOT / "configs" / "duecare" / "legal_claims.json").read_text(encoding="utf-8"))["claims"]}
    for myth in ce.MYTH_CATALOG:
        assert myth["corpus_anchor"], f"{myth['myth']}: no anchor"
        for anchor in myth["corpus_anchor"]:
            assert anchor in ids, f"dangling anchor {anchor!r} in myth {myth['myth']!r}"
