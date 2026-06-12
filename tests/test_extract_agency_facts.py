"""Offline tests for the agency-fact extractor, dossier builder, and search.

extract_facts is a pure deterministic extractor (no harness/network); the
dossier builder composes it with the suspicious-language scan + licensed-agency
verification.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load():
    path = _ROOT / "scripts" / "extract_agency_facts.py"
    spec = importlib.util.spec_from_file_location("dc_extract_agency_facts_test", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # frozen-dataclass exec needs registration
    spec.loader.exec_module(mod)
    return mod


EXF = _load()
REGISTRY = str(_ROOT / "data" / "agency_registry" / "sample_licensed_agencies.json")

AD = (
    "Easternwind Workforce Solutions (POEA-12345) is hiring!\n"
    "25 Domestic Helpers for Hong Kong, salary HKD 4,870/month.\n"
    "10 Welders for Saudi Arabia, SAR 2,500. Construction workers for Qatar.\n"
    "Contact: 0917-123-4567 or +63 2 8555 0101, email apply@easternwind.invalid\n"
    "Office: Unit 5, Sample Tower, Mabini Street, Ermita, Manila.\n"
    "Medical exam at St. Vincent Sample Medical Clinic. "
    "Pay placement fee and training fee before deployment."
)
BENIGN = (
    "Pinoy Cafe is hiring 2 baristas for our Quezon City branch. "
    "PHP 610/day plus SSS and PhilHealth. Apply in person Mon-Fri."
)


def test_extract_phones_have_no_fragments():
    facts = EXF.extract_facts(AD)
    assert "+63 2 8555 0101" in facts.phones
    assert "0917-123-4567" in facts.phones
    # the overlapping-regex fragments must be gone
    assert "17-123-4567" not in facts.phones
    assert "2 8555 0101" not in facts.phones


def test_extract_core_facts():
    facts = EXF.extract_facts(AD)
    assert any("Easternwind" in n for n in facts.agency_names)
    assert "POEA-12345" in facts.license_nos
    assert "apply@easternwind.invalid" in facts.emails
    assert any("Sample Tower" in a for a in facts.addresses)
    assert any("Medical Clinic" in c for c in facts.medical_clinics)
    assert facts.fee_mentions == ["placement fee", "training fee"]


def test_extract_job_orders_do_not_bleed_across_lines():
    facts = EXF.extract_facts(AD)
    by_dest = {o["destination"]: o for o in facts.job_orders}
    assert by_dest["Hong Kong"]["salary"] == "HKD 4,870"
    assert by_dest["Saudi Arabia"]["salary"] == "SAR 2,500"
    assert "Welder" in by_dest["Saudi Arabia"]["position"]
    # Qatar order had no salary on its clause -> empty, not the HK salary
    assert by_dest["Qatar"]["salary"] == ""


def test_extract_clinic_cue_when_no_named_clinic():
    facts = EXF.extract_facts("Apply now. Pre-employment medical and drug test required.")
    assert facts.medical_clinics
    assert "medical-exam requirement" in facts.medical_clinics[0]


def test_build_dossier_high_risk_for_redlisted_agency():
    # Easternwind is CANCELLED in the sample registry + the ad has fee language
    dossiers = EXF.build_dossier([{"id": "ad", "text": AD}], registry_path=REGISTRY)
    d = dossiers[0]
    assert d["risk_tier"] == "high"
    assert d["facts"]["license_nos"] == ["POEA-12345"]
    assert isinstance(d["agency_check"], list)


def test_build_dossier_low_risk_for_benign():
    dossiers = EXF.build_dossier([{"id": "ok", "text": BENIGN}], registry_path=REGISTRY)
    assert dossiers[0]["risk_tier"] == "low"


def test_search_dossiers_query_and_risk_filter():
    dossiers = EXF.build_dossier(
        [{"id": "bad", "text": AD}, {"id": "ok", "text": BENIGN}],
        registry_path=REGISTRY)
    # full-text query
    hits = EXF.search_dossiers("easternwind", dossiers)
    assert len(hits) == 1 and hits[0]["id"] == "bad"
    # structured risk filter
    high = EXF.search_dossiers("", dossiers, risk="high")
    assert [d["id"] for d in high] == ["bad"]
    low = EXF.search_dossiers("", dossiers, risk="low")
    assert [d["id"] for d in low] == ["ok"]


def test_cli_build_then_search(tmp_path):
    out = tmp_path / "dossiers"
    rc = EXF.main(["--text", AD, "--registry", REGISTRY, "--out", str(out)])
    assert rc == 0
    built = list(out.glob("dossier_*.json"))
    assert built
    # search the produced dossier file
    rc2 = EXF.main(["--search", "placement fee", "--from", str(built[0])])
    assert rc2 == 0
