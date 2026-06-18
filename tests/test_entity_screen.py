"""Tests for scripts/entity_screen.py -- the cross-register screening engine.

Pure, offline: synthetic entity records exercise the fuzzy matcher (precision on
distinctive tokens, invariance to legal suffixes), the risk classifier, and the
verdict logic (SANCTIONED / FLAGGED / LICENSED / NOT_FOUND).
"""
from __future__ import annotations

import difflib
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


es = _load("entity_screen", _ROOT / "scripts" / "entity_screen.py")

_RECS = [
    {"name": "Sunrise Overseas Recruitment Agency", "entity_type": "recruitment_agency",
     "jurisdiction": "PH", "status": "Cancelled", "source": "PH DMW"},
    {"name": "Bluewave Manpower Services", "entity_type": "recruitment_agency",
     "jurisdiction": "PH", "status": "Valid License", "source": "PH DMW"},
    {"name": "Redhawk Global Trading", "entity_type": "sanctioned_entity",
     "jurisdiction": "CN", "status": "watchlisted", "source": "OFAC SDN"},
    {"name": "Pacific Star Manpower", "entity_type": "recruitment_agency",
     "jurisdiction": "AE", "status": "Active", "source": "UAE register"},
]


# ---- sequence ratio (RapidFuzz optional, difflib fallback) ----------------

def test_seq_ratio_word_order_invariant_with_rapidfuzz():
    pytest.importorskip("rapidfuzz")
    # token_sort_ratio sorts tokens first -> reordering the same words scores ~1.0
    assert es._seq_ratio("sunrise overseas manpower", "manpower overseas sunrise") > 0.95


def test_seq_ratio_falls_back_to_difflib(monkeypatch):
    monkeypatch.setattr(es, "_rf_fuzz", None)
    assert es._seq_ratio("alpha beta", "alpha beta") == 1.0
    assert es._seq_ratio("alpha", "alphb") == difflib.SequenceMatcher(None, "alpha", "alphb").ratio()


# ---- match_score ----------------------------------------------------------

def test_identical_name_scores_high_and_is_strong():
    assert es.match_score("Sunrise Overseas Recruitment", "Sunrise Overseas Recruitment") >= 0.9


def test_legal_suffix_is_ignored():
    s = es.match_score("Sunrise Overseas Recruitment Agency",
                       "Sunrise Overseas Recruitment Agency, Inc.")
    assert s >= 0.84  # legal form does not distinguish two firms


def test_distinctive_token_difference_is_not_a_strong_match():
    # same generic words, different DISTINCTIVE word -> must not strong-match
    s = es.match_score("Sunrise Overseas Recruitment", "Sunset Overseas Recruitment")
    assert s < 0.84


def test_totally_different_names_score_low():
    assert es.match_score("Sunrise Recruitment", "Pacific Logistics Holdings") < 0.5


def test_empty_names_score_zero():
    assert es.match_score("", "Anything") == 0.0


# ---- risk_of --------------------------------------------------------------

def test_risk_classes():
    assert es.risk_of({"entity_type": "sanctioned_entity", "status": "watchlisted"}) == "CRITICAL"
    assert es.risk_of({"entity_type": "recruitment_agency", "status": "Cancelled"}) == "HIGH"
    assert es.risk_of({"entity_type": "recruitment_agency", "status": "Suspended"}) == "HIGH"
    assert es.risk_of({"entity_type": "recruitment_agency", "status": "Valid License"}) == "LICENSED"
    assert es.risk_of({"entity_type": "company", "status": ""}) == "UNKNOWN"


# ---- screen verdicts ------------------------------------------------------

def test_screen_flags_a_cancelled_match():
    res = es.screen("Sunrise Overseas Recruitment", _RECS)
    assert res["verdict"] == "FLAGGED" and res["found"]
    assert res["hits"][0]["risk"] == "HIGH"


def test_screen_passes_a_licensed_match():
    res = es.screen("Bluewave Manpower", _RECS)
    assert res["verdict"] == "LICENSED" and res["hits"][0]["status"] == "Valid License"


def test_screen_flags_a_sanctioned_match():
    res = es.screen("Redhawk Global Trading", _RECS)
    assert res["verdict"] == "SANCTIONED" and res["verdict_rank"] == 4


def test_screen_not_found_for_unknown_name():
    res = es.screen("Nonexistent Phantom Holdings", _RECS)
    assert res["verdict"] == "NOT_FOUND" and not res["found"]


def test_screen_country_filter_excludes_other_jurisdictions():
    # Pacific Star Manpower is AE; restricting to PH yields no hit
    res = es.screen("Pacific Star Manpower", _RECS, country="PH")
    assert not res["found"] and res["verdict"] == "NOT_FOUND"
    assert es.screen("Pacific Star Manpower", _RECS, country="AE")["found"]


def test_screen_hits_sorted_by_score_desc():
    res = es.screen("Sunrise Overseas Recruitment Agency", _RECS, threshold=0.1)
    scores = [h["score"] for h in res["hits"]]
    assert scores == sorted(scores, reverse=True)


def test_generic_only_query_does_not_false_match():
    # an all-generic query must not strong-match a specific agency
    res = es.screen("Overseas Recruitment Agency", _RECS)
    assert res["verdict"] in ("NOT_FOUND", "UNVERIFIED")
    assert all(h["score"] < 0.84 for h in res["hits"])
