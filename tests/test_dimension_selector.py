"""Tests for the per-prompt dimension relevance selector."""
from __future__ import annotations

import importlib
import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SCRIPTS = _ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

ds = importlib.import_module("dimension_selector")

_DIMS = [
    {"id": "response_quality.a", "group": "response_quality"},
    {"id": "ilo_indicator.deception", "group": "ilo_indicator"},
    {"id": "scheme_detection.x", "group": "scheme_detection"},
    {"id": "sector_awareness.domestic_work", "group": "sector_awareness"},
    {"id": "sector_awareness.fishing", "group": "sector_awareness"},
    {"id": "corridor_awareness.PH_HK", "group": "corridor_awareness"},
    {"id": "corridor_awareness.NP_GULF", "group": "corridor_awareness"},
    {"id": "pretext_resistance.a", "group": "pretext_resistance"},
    {"id": "financial_obfuscation_detection.a", "group": "financial_obfuscation_detection"},
    {"id": "benevolent_framing_resistance.a", "group": "benevolent_framing_resistance"},
    {"id": "legal_grounding.ilo_c029", "group": "legal_grounding"},
    {"id": "legal_grounding.ilo_p029_2014", "group": "legal_grounding"},
    {"id": "legal_grounding.palermo_protocol", "group": "legal_grounding"},
    {"id": "legal_grounding.ilo_c181", "group": "legal_grounding"},
    {"id": "legal_grounding.ilo_c095", "group": "legal_grounding"},
    {"id": "legal_grounding.ilo_c189", "group": "legal_grounding"},
    {"id": "legal_grounding.ilo_c188", "group": "legal_grounding"},
    {"id": "legal_grounding.mlc_2006", "group": "legal_grounding"},
    {"id": "legal_grounding.cedaw", "group": "legal_grounding"},
]


def test_worker_prompt_selects_matching_sector_only_and_no_attack_groups():
    meta = {"category": "sector_scenario", "framing": "worker_query",
            "sector": "domestic_work", "corridor": "PH_HK"}
    ids = set(ds.relevant_dim_ids(meta, _DIMS))
    assert "response_quality.a" in ids and "ilo_indicator.deception" in ids
    assert "sector_awareness.domestic_work" in ids          # matching sector
    assert "sector_awareness.fishing" not in ids            # other sector excluded
    assert "corridor_awareness.PH_HK" in ids
    assert "corridor_awareness.NP_GULF" not in ids
    assert "pretext_resistance.a" not in ids                # not an attack prompt


def test_pretext_jailbreak_selects_attack_groups_not_sector():
    meta = {"category": "pretext_jailbreak", "framing": "legitimizing_pretext"}
    ids = set(ds.relevant_dim_ids(meta, _DIMS))
    assert "pretext_resistance.a" in ids
    assert "scheme_detection.x" in ids                      # attack still implies scheme
    assert "sector_awareness.domestic_work" not in ids      # no sector tagged
    assert "corridor_awareness.PH_HK" not in ids


def test_financial_and_benevolent_triggers():
    assert "financial_obfuscation_detection.a" in set(ds.relevant_dim_ids(
        {"category": "money_mule", "framing": "mixed"}, _DIMS))
    assert "benevolent_framing_resistance.a" in set(ds.relevant_dim_ids(
        {"category": "benevolent_framing", "framing": "benevolent"}, _DIMS))


def test_selection_is_a_strict_subset():
    meta = {"category": "sector_scenario", "sector": "domestic_work"}
    ids = ds.relevant_dim_ids(meta, _DIMS)
    allids = {d["id"] for d in _DIMS}
    assert set(ids) <= allids and len(ids) < len(_DIMS)     # fewer than all


def test_judge_sector_and_corridor_aliases_normalize_to_rubric_ids():
    dims = [
        {"id": "sector_awareness.hospitality", "group": "sector_awareness"},
        {"id": "sector_awareness.domestic_work", "group": "sector_awareness"},
        {"id": "corridor_awareness.PH_GULF", "group": "corridor_awareness"},
        {"id": "corridor_awareness.PH_HK", "group": "corridor_awareness"},
    ]
    ids = set(ds.relevant_dim_ids(
        {"category": "rights_query"},
        dims,
        judge={"sector": "hotel", "corridor": "PH_SA"},
    ))
    assert "sector_awareness.hospitality" in ids
    assert "sector_awareness.domestic_work" not in ids
    assert "corridor_awareness.PH_GULF" in ids
    assert "corridor_awareness.PH_HK" not in ids


def test_legal_grounding_filters_to_universal_and_prompt_specific_statutes():
    meta = {
        "category": "sector_scenario",
        "framing": "worker_query recruitment fee wage deduction",
        "sector": "domestic_work",
    }
    ids = set(ds.relevant_dim_ids(meta, _DIMS))
    assert {
        "legal_grounding.ilo_c029",
        "legal_grounding.ilo_p029_2014",
        "legal_grounding.palermo_protocol",
        "legal_grounding.ilo_c181",
        "legal_grounding.ilo_c095",
        "legal_grounding.ilo_c189",
    } <= ids
    assert "legal_grounding.ilo_c188" not in ids
    assert "legal_grounding.mlc_2006" not in ids
    assert "legal_grounding.cedaw" not in ids


def test_fishing_legal_grounding_adds_fishing_instruments_not_domestic():
    meta = {
        "category": "sector_scenario",
        "framing": "worker_query vessel recruitment",
        "sector": "fishing",
    }
    ids = set(ds.relevant_dim_ids(meta, _DIMS))
    assert {
        "legal_grounding.ilo_c029",
        "legal_grounding.ilo_p029_2014",
        "legal_grounding.palermo_protocol",
        "legal_grounding.ilo_c181",
        "legal_grounding.ilo_c188",
        "legal_grounding.mlc_2006",
    } <= ids
    assert "legal_grounding.ilo_c189" not in ids


def test_2026_06_dimension_groups_select_correctly():
    dims = [{"id": g + ".a", "group": g} for g in
            ("coded_language_decoding", "digital_recruitment_awareness",
             "emergency_response_soundness", "evidence_specificity", "response_quality")]
    plain = set(ds.relevant_dim_ids({"category": "rights_query"}, dims))
    assert "coded_language_decoding.a" in plain               # CORE: always on
    assert "digital_recruitment_awareness.a" not in plain     # conditional, no trigger
    dig = set(ds.relevant_dim_ids({"category": "scam_compound", "framing": "social_media"}, dims))
    assert "digital_recruitment_awareness.a" in dig           # fires on scam / social_media
    emg = set(ds.relevant_dim_ids({"category": "sector_scenario", "framing": "locked in and threatened"}, dims))
    assert "emergency_response_soundness.a" in emg            # fires on locked / threatened
    worker = set(ds.relevant_dim_ids({"category": "sector_scenario", "sector": "domestic_work"}, dims))
    assert "evidence_specificity.a" in worker                # WORKER-scenario group
