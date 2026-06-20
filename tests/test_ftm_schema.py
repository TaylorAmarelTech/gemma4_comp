"""Tests for scripts/ftm_schema.py -- normalise entity records into the FtM model.

Pure/offline. Fixtures mirror the real shapes the connectors emit (GLEIF, DOL WHD,
OpenSanctions, BODS). Property names are the real FtM schema properties (verified from
the upstream schema YAMLs); the FtM library itself is optional (PyICU won't build here).
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


ftm = _load("ftm_schema", _ROOT / "scripts" / "ftm_schema.py")

GLEIF = {"name": "Sailwind Trading FZE", "lei": "254900N2EEPSHPNU0H50",
         "entity_type": "company", "jurisdiction": "AE", "status": "ISSUED",
         "registered_as": "DMCC-12345", "address": "Dubai, AE",
         "source": "GLEIF LEI (api.gleif.org, CC0)"}
UFLPA = {"name": "Huafu Hongsheng Cotton Co. Ltd.", "entity_type": "company",
         "jurisdiction": "US", "status": "uflpa_listed", "os_id": "NK-2HEWK3M5",
         "source": "US DHS UFLPA Entity List"}
AGENCY = {"name": "Sunrise Overseas Recruitment", "entity_type": "recruitment_agency",
          "jurisdiction": "PH", "license_no": "RL01", "status": "Cancelled"}
PERSON = {"name": "Jennifer Hewitson-Smith", "entity_type": "individual", "jurisdiction": "GB"}
EMPLOYER = {"name": "Mr. Q's Enterprises.", "entity_type": "employer", "jurisdiction": "US",
            "back_wages": 186357.0, "violations": 174, "industry": "Food service",
            "status": "violation"}


def test_schema_mapping():
    assert ftm.ftm_schema("company") == "Company" and ftm.ftm_schema("employer") == "Company"
    assert ftm.ftm_schema("individual") == "Person"
    assert ftm.ftm_schema("recruitment_agency") == "Organization"
    assert ftm.ftm_schema("regulator") == "PublicBody" and ftm.ftm_schema("vessel") == "Vessel"
    assert ftm.ftm_schema("sanctioned_entity") == "LegalEntity" and ftm.ftm_schema("") == "LegalEntity"


def test_gleif_company_maps_real_properties():
    e = ftm.to_ftm(GLEIF)
    assert e["schema"] == "Company" and e["id"] == "lei-254900N2EEPSHPNU0H50"  # LEI-keyed id
    p = e["properties"]
    assert p["name"] == ["Sailwind Trading FZE"]                    # FtM props are lists
    assert p["country"] == ["ae"]                                   # ISO-2 lowercased
    assert p["leiCode"] == ["254900N2EEPSHPNU0H50"]
    assert p["registrationNumber"] == ["DMCC-12345"]
    assert p["publisher"][0].startswith("GLEIF")


def test_uflpa_forced_labour_gets_export_control_topic():
    p = ftm.to_ftm(UFLPA)["properties"]
    assert "export.control" in p["topics"] and p["idNumber"] == ["NK-2HEWK3M5"]


def test_sanctioned_entity_topic_and_schema():
    e = ftm.to_ftm({"name": "Redhawk Global Trading", "entity_type": "sanctioned_entity",
                    "status": "watchlisted sanction"})
    assert e["schema"] == "LegalEntity" and "sanction" in e["properties"]["topics"]


def test_agency_uses_license_number_and_org_schema():
    e = ftm.to_ftm(AGENCY)
    assert e["schema"] == "Organization" and e["properties"]["licenseNumber"] == ["RL01"]
    assert e["properties"]["status"] == ["Cancelled"]


def test_person_schema_and_country():
    e = ftm.to_ftm(PERSON)
    assert e["schema"] == "Person" and e["properties"]["country"] == ["gb"]


def test_employer_notes_carry_enforcement_extras():
    notes = ftm.to_ftm(EMPLOYER)["properties"]["notes"][0]
    assert "back_wages=186357" in notes and "violations=174" in notes
    assert ftm.to_ftm(EMPLOYER)["properties"]["sector"] == ["Food service"]


def test_non_iso_jurisdiction_goes_to_jurisdiction_not_country():
    e = ftm.to_ftm({"name": "X Co", "entity_type": "company", "jurisdiction": "United Kingdom"})
    assert "country" not in e["properties"]                         # not a 2-letter code
    assert e["properties"]["jurisdiction"] == ["United Kingdom"]


def test_id_is_deterministic_and_hash_based_without_lei():
    rec = {"name": "Acme Ltd", "entity_type": "company", "jurisdiction": "AE"}
    assert ftm.to_ftm(rec)["id"] == ftm.to_ftm(rec)["id"]           # stable
    assert ftm.to_ftm(rec)["id"].startswith("dc-")                  # content hash, no LEI


def test_convert_skips_nameless_and_counts_schemas():
    ents = ftm.convert([GLEIF, PERSON, {"entity_type": "company"}])  # last has no name
    assert len(ents) == 2 and {e["schema"] for e in ents} == {"Company", "Person"}


def test_emit_records_toggles_native_vs_ftm():
    # the connector --ftm helper: passthrough when off, FtM EntityProxies when on
    assert ftm.emit_records([GLEIF, AGENCY], ftm=False) == [GLEIF, AGENCY]   # unchanged
    out = ftm.emit_records([GLEIF, AGENCY], ftm=True)
    assert {e["schema"] for e in out} == {"Company", "Organization"}
    assert out[0]["id"] == "lei-254900N2EEPSHPNU0H50"                        # converted
    assert ftm.emit_records([{"entity_type": "company"}], ftm=True) == []    # nameless dropped


def test_validate_falls_back_to_pure_when_library_absent():
    # validate=True must not raise even though followthemoney/PyICU won't import here
    e = ftm.to_ftm(GLEIF, validate=True)
    assert e["schema"] == "Company" and e["id"] == "lei-254900N2EEPSHPNU0H50"
