"""Tests for scripts/build_contract_dpo.py -- contract-derived hard-negative DPO pairs.

Pins the core guarantee: ablating exactly one chain link from a full gold trace yields a rejected that is
identical except for that missing link (statute or action), and only full-chain traces are eligible."""
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


bcd = _load("build_contract_dpo", _ROOT / "scripts" / "build_contract_dpo.py")
rc = _load("reasoning_contract", _ROOT / "scripts" / "reasoning_contract.py")

_FULL = ("This situation shows passport confiscation, a recognised ILO forced labour indicator. "
         "It is prohibited under ILO Convention No. 29 (Forced Labour). "
         "You should keep copies of your documents and do not hand over your passport to the recruiter. "
         "Contact your embassy and file a complaint with the labour office, which helps migrant workers.")


def _row(assistant, pid="T1"):
    return {"messages": [{"role": "user", "content": "My recruiter took my passport, what do I do?"},
                         {"role": "assistant", "content": assistant}], "_meta": {"prompt_id": pid}}


def test_ablate_statute_removes_only_the_citation():
    reduced = bcd.ablate_link(_FULL, "statute")
    assert reduced is not None
    v = rc.verify_reasoning(reduced)
    assert v.steps["statute"] is False                      # the citation is gone
    assert v.steps["indicator"] and v.steps["action"] and v.steps["resources"]   # everything else stays


def test_ablate_action_removes_only_the_action():
    reduced = bcd.ablate_link(_FULL, "action")
    assert reduced is not None
    v = rc.verify_reasoning(reduced)
    assert v.steps["action"] is False
    assert v.steps["indicator"] and v.steps["statute"] and v.steps["resources"]


def test_ablate_returns_none_when_link_absent():
    neutral = "The weather is mild and the report describes general background information only."
    assert bcd.ablate_link(neutral, "statute") is None
    assert bcd.ablate_link(neutral, "action") is None


def test_build_pairs_yields_one_hard_negative_per_present_link():
    doc = bcd.build_pairs([_row(_FULL)])
    pairs = doc["pairs"]
    assert doc["manifest"]["eligible_gold"] == 1
    assert {p["_meta"]["ablated_link"] for p in pairs} == {"statute", "action"}
    for p in pairs:
        assert p["chosen"] == _FULL                         # chosen is the untouched gold trace
        assert p["rejected"] != _FULL and len(p["rejected"]) < len(_FULL)   # rejected is strictly reduced
        assert p["prompt"].startswith("My recruiter")        # the user turn carried through


def test_non_satisfying_trace_is_not_eligible():
    doc = bcd.build_pairs([_row("I'm sorry, but I can't help with that.")])
    assert doc["manifest"]["eligible_gold"] == 0 and doc["pairs"] == []
