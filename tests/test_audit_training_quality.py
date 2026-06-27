"""Tests for scripts/audit_training_quality.py -- pre-train data-quality guards.

Each test pins one failure mode the audit is meant to catch: cross-split leakage (overfitting),
DPO length-bias (false pattern), single-corridor typology (jurisdiction shortcut), and fragile-fact
assertion (volatile specifics that should live in tools/RAG, not the weights)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "scripts"))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


atq = _load("audit_training_quality", _ROOT / "scripts" / "audit_training_quality.py")


@pytest.mark.skipif(not atq._HAVE_SIMHASH, reason="research_tools.dedup SimHash unavailable")
def test_near_dup_leakage_flags_heldout_copy():
    # Arrange: a heldout prompt that duplicates a train prompt (the leak the split must not contain).
    # SimHash@dist<=3 is deliberately conservative -- it catches near-identical re-copies, not genuine
    # paraphrases -- so the leak case is an exact copy and the clean case is a clearly distinct prompt.
    train = ["A recruiter in Nepal is charging a worker a large fee for a job in Qatar, is this legal?"]
    leak_ho = [train[0]]
    fresh_ho = ["My employer in Taiwan took my passport on arrival; what are my rights as a fisher?"]
    # Act
    leaked = atq.near_dup_leakage(train, leak_ho)
    clean = atq.near_dup_leakage(train, fresh_ho)
    # Assert
    assert leaked["available"] and leaked["leaked"] == 1 and leaked["ok"] is False
    assert clean["leaked"] == 0 and clean["ok"] is True


def test_length_bias_flags_long_chosen():
    long_chosen = [{"chosen": "x" * 1000, "rejected": "y" * 100} for _ in range(5)]   # 10x ratio
    balanced = [{"chosen": "x" * 320, "rejected": "y" * 300} for _ in range(5)]
    assert atq.length_bias(long_chosen)["ok"] is False
    assert atq.length_bias(long_chosen)["chosen_over_rejected_ratio"] == 10.0
    assert atq.length_bias(balanced)["ok"] is True
    assert atq.length_bias([])["n"] == 0


def test_corridor_diversity_flags_dense_single_corridor():
    # debt_bondage spans TWO corridors (ok); passport_confiscation is DENSE but in ONE corridor (risk);
    # rare_style is single-corridor but too sparse to flag. min_rows=2 keeps the fixture small.
    pid_meta = {
        "P1": {"category": "debt_bondage", "corridor": "Nepal->Qatar"},
        "P2": {"category": "debt_bondage", "corridor": "Bangladesh->Malaysia"},
        "P3": {"category": "passport_confiscation", "corridor": "Nepal->Qatar"},
        "P4": {"category": "passport_confiscation", "corridor": "Nepal->Qatar"},
        "P5": {"category": "rare_style", "corridor": "India->Kuwait"},   # only 1 row -> sparse, not flagged
    }
    rows = [{"_meta": {"prompt_id": p}} for p in pid_meta]
    out = atq.corridor_diversity(rows, pid_meta, min_rows=2)
    assert out["distinct_corridors"] == 3
    assert "passport_confiscation" in out["dense_single_corridor_typologies"]   # 2 rows, 1 corridor -> risk
    assert "debt_bondage" not in out["dense_single_corridor_typologies"]        # 2 corridors -> ok
    assert "rare_style" not in out["dense_single_corridor_typologies"]          # 1 row -> too sparse
    assert out["multi_corridor_typologies"] == 1 and out["sparse_typologies"] == 1
    assert out["ok"] is False


def test_fragile_fact_assertions_flags_phone_and_counts_money_date():
    gold = [
        "Call the hotline at +1 555 0100 right away.",          # phone-like -> fragile (must be ~0)
        "The recruitment fee was $4,500 which exceeds the cap.",  # money amount -> informational
        "This rule changed in 2023 for that corridor.",          # explicit date -> informational
        "Keep your contract and payslips and seek free legal aid.",  # clean grounded reply
    ]
    out = atq.fragile_fact_assertions(gold)
    assert out["n"] == 4
    assert out["with_phone_like"] == 1 and out["ok_phone"] is False
    assert out["with_money_amount"] == 1
    assert out["with_explicit_date"] == 1


def test_fragile_fact_clean_gold_passes_phone_gate():
    gold = ["Keep your contract and payslips; you can raise a wage claim with the labour office."]
    out = atq.fragile_fact_assertions(gold)
    assert out["with_phone_like"] == 0 and out["ok_phone"] is True


def test_sft_helpers_extract_roles():
    row = {"messages": [{"role": "user", "content": "u"}, {"role": "assistant", "content": "a"}]}
    assert atq._sft_user(row) == "u"
    assert atq._sft_assistant(row) == "a"
    assert atq._sft_user({}) == "" and atq._sft_assistant({}) == ""
