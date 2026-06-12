"""Offline tests for the licensed-agency verification registry.

Covers name/status normalization, every verification verdict
(licensed_valid / licensed_red for expired-cancelled-delisted-suspended /
not_found / licence mismatch), the committed synthetic sample's integrity
(no real PII), and the CLI.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load():
    path = _ROOT / "scripts" / "agency_registry.py"
    spec = importlib.util.spec_from_file_location("dc_agency_registry_test", path)
    mod = importlib.util.module_from_spec(spec)
    # Register before exec: a frozen dataclass's KW_ONLY check does
    # sys.modules.get(cls.__module__).__dict__, which is None otherwise.
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


AR = _load()
REGISTRY = AR.load_registry()  # default committed synthetic sample


def test_sample_registry_is_synthetic_and_well_formed():
    raw = json.loads((AR.DEFAULT_REGISTRY).read_text(encoding="utf-8"))
    assert raw["_synthetic"] is True
    assert len(REGISTRY) == raw["n_records"] == 10
    # exercises every status the verifier branches on
    statuses = {p.status for p in REGISTRY}
    assert {"valid", "expired", "cancelled", "delisted", "suspended"} <= statuses
    # synthetic-safety: no plausibly-real contact data leaked in
    for p in REGISTRY:
        assert "SAMPLE" in p.license_no.upper() or "sample" in p.name.lower()
        for ph in p.phones:
            assert "555" in ph  # fictional exchange


def test_normalize_name_strips_suffixes():
    assert AR.normalize_name("Sunrise Overseas Manpower Services, Inc.") == "sunrise"
    assert AR.normalize_name("Pacific Bridge Recruitment Corporation") == "pacific bridge"


def test_verify_valid_agency():
    v = AR.verify_agency("Sunrise Overseas Manpower Services", REGISTRY)
    assert v.status == "licensed_valid"
    assert v.license_status == "valid"
    assert "positive signal" in v.advisory


def test_verify_not_found_is_red_flag():
    v = AR.verify_agency("Totally Fake Recruiters of Nowhere", REGISTRY)
    assert v.status == "not_found"
    assert "red flag" in v.advisory.lower()


def test_verify_expired_and_cancelled_are_red():
    assert AR.verify_agency("Goldfield International Manpower", REGISTRY).status == "licensed_red"
    assert AR.verify_agency("Easternwind Workforce Solutions", REGISTRY).status == "licensed_red"
    delisted = AR.verify_agency("Crown Horizon Recruitment Agency", REGISTRY)
    assert delisted.status == "licensed_red" and delisted.license_status == "delisted"


def test_verify_license_mismatch_is_red():
    # right name, wrong licence number -> impersonation / pass-through signal
    v = AR.verify_agency("Sunrise Overseas Manpower Services", REGISTRY,
                         claimed_license="POEA-SAMPLE-9999-LB")
    assert v.status == "licensed_red"
    assert v.license_match == "mismatch"


def test_verify_license_match_stays_valid():
    v = AR.verify_agency("Sunrise Overseas Manpower Services", REGISTRY,
                         claimed_license="POEA-SAMPLE-1001-LB")
    assert v.status == "licensed_valid"
    assert v.license_match == "match"


def test_medical_clinic_record_type():
    v = AR.verify_agency("St. Vincent Sample Medical Clinic", REGISTRY)
    assert v.record_type == "medical_clinic"
    assert v.status == "licensed_valid"


def test_token_overlap_fallback_matches_partial_name():
    # missing the corporate suffix still matches on >=2 shared tokens
    v = AR.verify_agency("Pacific Bridge", REGISTRY)
    assert v.matched_name.startswith("Pacific Bridge")


def test_cli_query(capsys):
    rc = AR.main(["--query", "Easternwind Workforce Solutions"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "licensed_red"
    assert out["license_status"] == "cancelled"
