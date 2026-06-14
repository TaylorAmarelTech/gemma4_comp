"""Tests for scripts/migrant_taxonomy.py -- industry/skill/problem taxonomy + ranking.

Pure, offline: validates the taxonomy's internal consistency (every problem maps
to a real ILO indicator, every industry's problems exist) and the source-ranking
that turns the catalogue into a prioritised pull queue.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


tx = _load("migrant_taxonomy", _ROOT / "scripts" / "migrant_taxonomy.py")


# ---- internal consistency -------------------------------------------------

def test_every_problem_maps_to_a_real_ilo_indicator():
    for pid, p in tx.PROBLEMS.items():
        assert p["ilo_indicator"] in tx.ILO_INDICATORS, pid
        assert p["severity"] in (1, 2, 3)
        assert p["label"] and p["description"]


def test_every_industry_profile_is_valid():
    for ind, prof in tx.INDUSTRY_PROFILES.items():
        assert prof.skill_level in tx.SKILL_LEVELS, ind
        assert prof.risk_tier in (1, 2, 3), ind
        for pid in prof.problems:
            assert pid in tx.PROBLEMS, f"{ind}->{pid}"


def test_all_eighteen_catalogue_industries_profiled():
    expected = {"recruitment_agency", "manning_agency", "medical_clinic", "training_center",
                "money_lender", "financial_services", "remittance", "hotel", "security_services",
                "company_registry", "construction", "fishing_seafood", "manufacturing",
                "agriculture", "domestic_worker", "care_home", "facility_management", "other"}
    assert set(tx.INDUSTRY_PROFILES) == expected


# ---- lookups --------------------------------------------------------------

def test_profile_lookup_case_insensitive():
    assert tx.profile("FISHING_SEAFOOD").risk_tier == 1
    assert tx.profile("nope") is None


def test_fishing_and_domestic_are_tier1_severe():
    assert tx.profile("fishing_seafood").risk_tier == 1
    assert tx.profile("domestic_worker").risk_tier == 1
    assert tx.profile("financial_services").risk_tier == 3  # screening layer, not a labour site


def test_problems_for_industry_severity_sorted():
    probs = tx.problems_for_industry("fishing_seafood")
    assert probs and all(probs[i]["severity"] >= probs[i + 1]["severity"] for i in range(len(probs) - 1))
    assert any(p["id"] == "movement_restriction" for p in probs)


def test_industries_by_risk_tier_partitions_all():
    byt = tx.industries_by_risk_tier()
    total = sum(len(v) for v in byt.values())
    assert total == len(tx.INDUSTRY_PROFILES)
    assert "construction" in byt[1] and "hotel" in byt[2]


def test_industries_by_skill_covers_unskilled_and_skilled():
    bys = tx.industries_by_skill()
    assert "fishing_seafood" in bys["unskilled"]
    assert "money_lender" in bys["skilled"]
    assert "manufacturing" in bys["semi_skilled"]


# ---- ranking --------------------------------------------------------------

def _src(**over):
    base = {"id": "x", "name": "X", "country": "PH", "industry": "recruitment_agency",
            "official": True, "url_verified": True, "has_data_endpoint": True, "access_tier": "free"}
    base.update(over)
    return base


def test_readiness_score_rewards_endpoint_and_provenance():
    full = tx.readiness_score(_src())
    none = tx.readiness_score(_src(official=False, url_verified=False,
                                   has_data_endpoint=False, access_tier="paid"))
    assert full > 0.9 and none == 0.0
    # an endpoint is worth more than provenance alone
    assert tx.readiness_score(_src(official=False, url_verified=False, access_tier="paid")) == 0.35


def test_rank_high_risk_ready_source_beats_low_risk():
    ranked = tx.rank_sources([
        _src(id="lowrisk", industry="financial_services"),
        _src(id="hirisk", industry="fishing_seafood"),
    ])
    assert ranked[0]["id"] == "hirisk"  # tier1 fishing outranks tier3 finance at equal readiness
    assert ranked[0]["priority"] >= ranked[1]["priority"]
    assert {"risk_tier", "readiness", "priority"} <= set(ranked[0])


def test_rank_unready_high_risk_loses_to_ready_high_risk():
    ranked = tx.rank_sources([
        _src(id="ready", industry="construction"),
        _src(id="unready", industry="construction", has_data_endpoint=False,
             url_verified=False, official=False, access_tier="login"),
    ])
    assert ranked[0]["id"] == "ready"


def test_rank_respects_top_limit():
    srcs = [_src(id=str(i)) for i in range(10)]
    assert len(tx.rank_sources(srcs, top=3)) == 3


def test_summary_shape():
    s = tx.summary()
    assert s["industries"] == 18 and s["ilo_indicators"] == 11
    assert set(s["by_risk_tier"]) == {"severe", "elevated", "baseline"}
    assert set(s["by_skill"]) == set(tx.SKILL_LEVELS)
