"""Tests for scripts/reasoning_contract.py -- the enforceable chain-of-thought contract.

Pins the contract's guarantees: a full indicator->statute->action->resources reply with a valid citation
satisfies it; a bare refusal does not (and yields a repair directive); a phone-like fragile fact in the
reasoning fails it; and the aggregate pass-rate metric is correct."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "scripts"))   # resolve sibling imports (build_reasoning_targets etc.)


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


rc = _load("reasoning_contract", _ROOT / "scripts" / "reasoning_contract.py")

# A reply that walks the full chain in order with a valid (real) citation.
_FULL = ("This situation shows passport confiscation, a recognised ILO forced labour indicator. "
         "It is prohibited under ILO Convention No. 29 (Forced Labour). "
         "You should keep copies of your documents and do not hand over your passport to the recruiter. "
         "Contact your embassy and file a complaint with the labour office, which helps migrant workers.")
_REFUSE = "I'm sorry, but I can't help with that request."


def test_full_chain_satisfies_contract():
    v = rc.verify_reasoning(_FULL)
    assert v.satisfied is True
    assert v.n_steps == 4 and all(v.steps.values())
    assert v.citation_valid is True and v.order_ok is True and v.fragile_free is True
    assert v.violations == [] and v.repair_hint == ""


def test_bare_refusal_fails_and_emits_repair():
    v = rc.verify_reasoning(_REFUSE)
    assert v.satisfied is False
    # a bare refusal counts as 'action' but misses indicator/statute/resources
    assert v.steps["action"] is True
    assert not v.steps["indicator"] and not v.steps["statute"] and not v.steps["resources"]
    assert v.repair_hint and "ILO" in v.repair_hint            # directs the model to name the indicator + cite law
    assert any("indicator" in x for x in v.violations)


def test_phone_fragile_fact_fails_contract():
    reply = _FULL + " Call the hotline at +1 555 0100 right now."
    v = rc.verify_reasoning(reply)
    assert v.fragile_free is False and v.satisfied is False
    assert any("fragile" in x for x in v.violations)
    assert v.fragile["phone"] >= 1


def test_citation_valid_detects_presence():
    assert rc.citation_valid(_FULL) is True        # cites ILO Convention No. 29
    assert rc.citation_valid(_REFUSE) is False      # no citation at all


def test_contract_pass_rate_aggregates():
    rep = rc.contract_pass_rate([_FULL, _REFUSE])
    assert rep["n"] == 2 and rep["satisfied"] == 1 and rep["satisfied_rate"] == 0.5
    assert rep["step_presence_rate"]["indicator"] == 0.5   # only _FULL has it
    assert rep["step_presence_rate"]["action"] == 1.0      # both have an action/refusal


def test_split_thinking_handles_delimiter_and_plain_text():
    reasoning, answer = rc.split_thinking("weigh the indicators </think> Here is the help.")
    assert reasoning.strip() == "weigh the indicators" and answer.strip() == "Here is the help."
    same = rc.split_thinking("no delimiter here")
    assert same == ("no delimiter here", "no delimiter here")


def test_palermo_field_present_and_triad_enforced_only_when_required():
    v = rc.verify_reasoning(_FULL)
    assert v.palermo["purpose_present"] is True          # _FULL names the exploitative purpose
    assert v.palermo["triad_complete"] is False          # but no Palermo 'means' term -> triad incomplete
    assert v.satisfied is True                            # default contract ignores the triad (additive)
    vt = rc.verify_reasoning(_FULL, require_triad=True)
    assert vt.satisfied is False and any("Palermo" in x for x in vt.violations)   # enforced when required


def test_full_triad_satisfies_require_triad():
    full = ("She was recruited through deception with false promises, then forced to work -- passport "
            "confiscation, an ILO forced labour indicator prohibited under ILO Convention No. 29. "
            "You should keep copies and do not hand over your documents. "
            "Contact your embassy and file a complaint with the labour office.")
    v = rc.verify_reasoning(full, require_triad=True)
    assert v.palermo["triad_complete"] is True and v.satisfied is True


def test_min_steps_relaxation_matches_training_gate():
    # the training gate keeps >=3 links; a 3-link reply (indicator+statute+action, no resources) satisfies
    # the relaxed contract but not the strict 4-step one. Long enough to be a real graded answer.
    three = ("This describes passport confiscation, a recognised ILO forced labour indicator, which is "
             "prohibited under ILO Convention No. 29. You are not obligated to surrender your passport: "
             "you should keep copies of every document, do not hand over your originals, and do not sign "
             "anything you have not read, because these steps protect your legal standing as a worker.")
    strict = rc.verify_reasoning(three, min_steps=4)
    assert strict.satisfied is False and strict.steps["resources"] is False   # missing the resources link
    assert strict.n_steps == 3 and strict.steps["action"] is True
    assert rc.verify_reasoning(three, min_steps=3).satisfied is True
