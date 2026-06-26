"""Tests for scripts/build_reasoning_targets.py -- the indicator->statute->action->resources chain gate."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "scripts"))   # so sibling imports (citation/refusal/taxonomy) resolve


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


br = _load("build_reasoning_targets", _ROOT / "scripts" / "build_reasoning_targets.py")


def _sft(pid, assistant):
    return {"messages": [{"role": "user", "content": f"q-{pid}"},
                         {"role": "assistant", "content": assistant}], "_meta": {"prompt_id": pid}}


_FULL = ("I can't help structure recruitment fees to evade the cap. What you describe is debt bondage, a "
         "forced-labour indicator, and under ILO Convention C181 charging workers illegal fees is prohibited. "
         "You are not obligated to pay it; keep copies of every receipt and contract. Contact the national "
         "labour regulator or your embassy, and you can file a complaint.")
_PARTIAL = ("I won't help with that. This is contract substitution and deception that ILO Convention C181 "
            "covers; you are not obligated to accept the swapped terms and should keep copies of the original "
            "signed contract for your own records going forward in case you need them later.")
_BARE = ("I'm sorry, but I cannot help with that request. I am not able to assist with what you are asking, "
         "and I would encourage you to reconsider whether this is appropriate before proceeding any further "
         "with the approach that you described to me just now in your message.")


def test_chain_links_detects_full_chain():
    assert br.chain_links(_FULL) == {"indicator": True, "statute": True, "action": True, "resources": True}


def test_bare_refusal_is_action_only():
    links = br.chain_links(_BARE)
    assert links["action"] is True                         # a refusal IS a graded action (not a format failure)
    assert not (links["indicator"] or links["statute"] or links["resources"])
    assert sum(links.values()) == 1                        # bare refusal = 1/4 chain links


def test_partial_chain_missing_resources():
    links = br.chain_links(_PARTIAL)
    assert links["indicator"] and links["statute"] and links["action"]
    assert links["resources"] is False                     # names indicator+law+action but no resource pointer
    assert sum(links.values()) == 3


def test_build_gates_and_annotates():
    doc = br.build([_sft("p1", _FULL), _sft("p2", _PARTIAL), _sft("p3", _BARE)], min_chain=3)
    m = doc["manifest"]
    assert m["input"] == 3 and m["kept"] == 2              # full(4) + partial(3) kept; bare(1) dropped
    assert {r["_meta"]["prompt_id"] for r in doc["rows"]} == {"p1", "p2"}
    p1 = next(r for r in doc["rows"] if r["_meta"]["prompt_id"] == "p1")
    assert p1["_meta"]["chain_completeness"] == 4 and p1["_meta"]["chain_links"]["resources"] is True
    assert m["link_presence"]["action"] == 3              # all three state an action (incl. the bare refusal)
    assert m["link_presence"]["resources"] == 1           # only the full target points to resources
    assert m["completeness_distribution"]["1"] == 1       # the bare refusal


def test_build_min_chain_4_is_stricter():
    doc = br.build([_sft("p1", _FULL), _sft("p2", _PARTIAL)], min_chain=4)
    assert doc["manifest"]["kept"] == 1                    # only the full 4/4 chain survives min_chain=4
