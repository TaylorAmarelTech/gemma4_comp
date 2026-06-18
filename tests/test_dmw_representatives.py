"""Tests for scripts/dmw_representatives.py -- DMW reps -> individual entities.

Offline, synthetic agency records. Covers rep extraction from notes, de-dup of a
person across agencies, and the active/inactive status from agency standing.
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


dr = _load("dmw_representatives", _ROOT / "scripts" / "dmw_representatives.py")


def test_parse_rep_from_notes():
    assert dr.parse_rep("license RL01; rep: JUAN DELA CRUZ; data_as_of 2026") == "JUAN DELA CRUZ"
    assert dr.parse_rep("no rep here") == ""


def test_dedups_a_person_across_agencies_and_aggregates():
    recs = [
        {"name": "Alpha Manpower Inc", "status": "valid", "notes": "rep: JUAN DELA CRUZ"},
        {"name": "Beta Recruitment Corp", "status": "expired", "notes": "rep: JUAN DELA CRUZ"},
        {"name": "Gamma Agency", "status": "valid", "notes": "rep: MARIA SANTOS"},
    ]
    out = dr.agency_records_to_individuals(recs)
    assert len(out) == 2                       # JUAN deduped across his two agencies
    juan = next(e for e in out if e["name"] == "JUAN DELA CRUZ")
    assert juan["entity_type"] == "individual" and juan["jurisdiction"] == "PH"
    assert juan["role"] == "agency_representative"
    assert "Alpha Manpower Inc" in juan["notes"] and "Beta Recruitment Corp" in juan["notes"]
    assert "2 PH recruitment agencies" in juan["notes"]


def test_status_active_if_any_agency_valid_else_inactive():
    out = dr.agency_records_to_individuals([
        {"name": "Valid Co", "status": "valid", "notes": "rep: ACTIVE PERSON"},
        {"name": "Expired Co", "status": "expired", "notes": "rep: INACTIVE PERSON"},
    ])
    by = {e["name"]: e for e in out}
    assert by["ACTIVE PERSON"]["status"] == "active"
    assert by["INACTIVE PERSON"]["status"] == "inactive"   # no valid agency -> flag-worthy


def test_records_without_a_rep_are_skipped():
    out = dr.agency_records_to_individuals([{"name": "No Rep Co", "status": "valid", "notes": "x"}])
    assert out == []
