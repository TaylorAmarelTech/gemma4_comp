from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def _rule(**overrides: object) -> dict:
    rule = {
        "rule": "usury_pattern_high_apr",
        "patterns": [r"\b(\d{2,3})\s*%\s*apr\b"],
        "severity": "high",
        "citation": "ILO C029 (Forced Labour) §2; HK Money Lenders Ord. Cap. 163 §24",
        "indicator": "Predatory APR; ILO forced-labor indicator 2 (debt bondage).",
    }
    rule.update(overrides)
    return rule


def test_extract_sources_keeps_distinct_instruments() -> None:
    from duecare.chat.rulecards import extract_authoritative_sources

    sources = extract_authoritative_sources(
        "ILO C029 §1 + ILO C095 Art. 8; Palermo Protocol; RA 8042; HK Cap. 57"
    )
    assert "ILO C029" in sources and "ILO C095" in sources
    assert "palermo_protocol" in sources
    assert "RA 8042" in sources
    assert "HK Cap. 57" in sources
    # ILO C029 and ILO C095 must not collapse into one token.
    assert len([s for s in sources if s.startswith("ILO C")]) == 2


def test_infer_jurisdictions_is_bounded_and_deduped() -> None:
    from duecare.chat.rulecards import infer_jurisdictions

    assert infer_jurisdictions("HK Cap. 57; RA 8042 (Philippines)") == ["HK", "PH"]
    assert infer_jurisdictions("no recognized jurisdiction token here") == []


def test_compile_rule_classifies_as_labeling_function_not_invariant() -> None:
    from duecare.chat.rulecards import (
        ROLE_FEATURE_EXTRACTOR,
        ROLE_HARD_INVARIANT,
        ROLE_LABELING_FUNCTION,
        compile_rule,
    )

    card = compile_rule(_rule(), category="A: DEBT BONDAGE")
    assert ROLE_LABELING_FUNCTION in card.roles
    assert ROLE_FEATURE_EXTRACTOR in card.roles
    # A pattern match is grounds for inquiry, not proof: never an auto-invariant.
    assert ROLE_HARD_INVARIANT not in card.roles
    assert card.candidate_invariant_review is False  # severity high, not critical


def test_critical_rule_is_flagged_for_invariant_review_but_not_auto_promoted() -> None:
    from duecare.chat.rulecards import ROLE_HARD_INVARIANT, compile_rule

    card = compile_rule(_rule(severity="critical"), category="A: DEBT BONDAGE")
    assert card.candidate_invariant_review is True
    assert ROLE_HARD_INVARIANT not in card.roles


def test_every_card_records_its_calibration_gaps() -> None:
    from duecare.chat.rulecards import compile_rule

    card = compile_rule(_rule(), category="A")
    assert "expected_precision_recall_unknown" in card.calibration_gaps
    assert "no_unit_test_counterexamples" in card.calibration_gaps
    missing = compile_rule(_rule(citation=""), category="A")
    assert "missing_authoritative_source" in missing.calibration_gaps


def test_independence_report_collapses_correlated_witnesses() -> None:
    from duecare.chat.rulecards import compile_deck, independence_report

    rules = [
        _rule(rule="a", citation="Palermo Protocol"),
        _rule(rule="b", citation="Palermo Protocol"),
        _rule(rule="c", citation="Palermo Protocol"),
        _rule(rule="d", citation="ILO C189"),
    ]
    report = independence_report(compile_deck(rules, ["X", "X", "X", "Y"]))
    assert report["total_rules"] == 4
    # 3 Palermo rules are one witness family, not three confirmations.
    assert report["effective_independent_families"] == 2
    assert report["largest_family_rule_count"] == 3
    assert report["rules_per_authoritative_source"]["palermo_protocol"] == 3


def test_effective_witness_count_matches_design_effect_bounds() -> None:
    from duecare.chat.rulecards import effective_witness_count

    sizes = [3, 1]  # one family of 3 correlated rules, one singleton
    # rho=0 -> every rule independent -> 4
    assert effective_witness_count(sizes, 0.0) == 4.0
    # rho=1 -> each family collapses to one witness -> 2
    assert effective_witness_count(sizes, 1.0) == 2.0
    # rho=0.5 -> 3/(1+2*0.5) + 1 = 1.5 + 1 = 2.5
    assert effective_witness_count(sizes, 0.5) == 2.5
    # clamps out-of-range rho
    assert effective_witness_count(sizes, 2.0) == 2.0


def test_independence_report_includes_effective_witnesses_by_rho() -> None:
    from duecare.chat.rulecards import compile_deck, independence_report

    rules = [
        _rule(rule="a", citation="Palermo Protocol"),
        _rule(rule="b", citation="Palermo Protocol"),
        _rule(rule="c", citation="ILO C189"),
    ]
    report = independence_report(compile_deck(rules, ["X", "X", "Y"]))
    eff = report["effective_witnesses_by_rho"]
    # rho=0.9: 2/(1+1*0.9) + 1 = 1.0526 + 1 ~= 2.05
    assert eff["rho_0.9"] == 2.05
    # effective count at any rho sits between family count (2) and total (3)
    assert all(2.0 <= v <= 3.0 for v in eff.values())


def test_uncited_rule_falls_back_to_category_family() -> None:
    from duecare.chat.rulecards import compile_deck, independence_report

    report = independence_report(
        compile_deck([_rule(rule="z", citation="")], ["orphan_category"])
    )
    assert "category:orphan_category" in report["families"]


def test_compile_deck_rejects_mismatched_category_length() -> None:
    import pytest
    from duecare.chat.rulecards import compile_deck

    with pytest.raises(ValueError):
        compile_deck([_rule()], ["A", "B"])


def test_compiles_the_real_grep_deck_into_fewer_families_than_rules() -> None:
    import importlib.util

    from duecare.chat.rulecards import (
        compile_deck,
        deck_summary,
        independence_report,
    )

    grep_path = _SRC / "duecare" / "chat" / "harness" / "_grep_rules.py"
    spec = importlib.util.spec_from_file_location("_grep_rules_probe", grep_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rules = list(module.GREP_RULES)

    cards = compile_deck(rules)
    report = independence_report(cards)
    summary = deck_summary(cards)
    assert report["total_rules"] == len(rules) >= 400
    # The whole point: many rules, far fewer independent witness families.
    assert report["effective_independent_families"] < report["total_rules"]
    assert summary["cards_with_authoritative_source"] > 0
    # Palermo is the single most-cited instrument in the real deck.
    top_source = next(iter(report["rules_per_authoritative_source"]))
    assert top_source == "palermo_protocol"
