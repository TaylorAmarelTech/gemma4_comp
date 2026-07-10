"""Legal CoT training generator: chosen answers must PASS the reasoning contract, the structural failure
modes must FAIL it, and the overbroad-no-exception mode must SLIP the structural contract (the gap the
faithfulness/exception layer owns) -- the two-layer split, pinned."""
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
bt = _load("build_legal_cot_training", _ROOT / "scripts" / "build_legal_cot_training.py")


def _run():
    return bt.generate(bt.lr.SCENARIOS, bt.lr.load_claims(), date(2026, 7, 10))


def test_every_chosen_passes_the_reasoning_contract():
    out = _run()
    assert out["gate"]["chosen_pass"] == len(bt.lr.SCENARIOS)   # all chosen answers satisfy the contract
    assert out["gate"]["chosen_fail"] == 0
    for row in out["sft"]:
        assert row["_contract_ok"] is True                     # never an SFT target that fails the contract
        assert row["messages"][1]["role"] == "assistant"


def test_structural_failure_modes_are_rejected_by_the_contract():
    out = _run()
    by = out["gate"]["by_mode"]
    for mode in ("conclusion_only", "refusal_collapse", "fabricated_citation",
                 "stale_fact_memorized", "missing_resources"):
        assert by[mode]["rejected_failed_contract"] == by[mode]["n"]   # every rejected fails the contract


def test_overbroad_is_the_semantic_gap_the_contract_misses():
    out = _run()
    ob = out["gate"]["by_mode"]["overbroad_no_exception"]
    assert ob["rejected_failed_contract"] == 0                  # a real convention cited WITHOUT its exception
    # ... passes the STRUCTURAL contract -> it is the gap the faithfulness/exception layer owns
    pairs = [d for d in out["dpo"] if d["failure_mode"] == "overbroad_no_exception"]
    assert pairs and all(d["chosen_contract_ok"] and d["rejected_contract_ok"] for d in pairs)


def test_dpo_pairs_are_chosen_over_rejected_with_a_labelled_failure_mode():
    out = _run()
    assert out["dpo"]                                           # pairs emitted
    for d in out["dpo"]:
        assert d["chosen"] != d["rejected"]
        assert d["failure_mode"] in bt.FAILURE_MODES
        assert d["chosen_contract_ok"] is True                 # chosen always passes; that's the preference signal


def test_chosen_defers_volatile_facts_instead_of_memorising_them():
    # the chosen answer must NOT assert a phone number or a fixed fee -- it defers them (rule 81 / anti-stale)
    out = _run()
    chosen = out["sft"][0]["messages"][1]["content"]
    assert "looked up fresh" in chosen and "verify" in chosen.lower()
