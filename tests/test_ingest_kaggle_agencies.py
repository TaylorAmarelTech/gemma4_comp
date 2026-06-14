"""Tests for scripts/ingest_kaggle_agencies.py -- map Kaggle CSV exports to entities.

Offline: writes tiny synthetic CSVs (same column shape as the real DMW exports)
and checks the agency + job-order -> EntityRecord mapping, including employers
derived from PRINCIPALNAME and jobsite->country-code corridor.
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


ik = _load("ingest_kaggle_agencies", _ROOT / "scripts" / "ingest_kaggle_agencies.py")


def test_agency_csv_maps_to_recruitment_agency(tmp_path):
    p = tmp_path / "ag.csv"
    p.write_text(
        "Agency,AgencyAddress,MunicipalityCity,CityProvince,ContactNo,Website,eMail,"
        "LicenseStatus,DataAsOf,AgencyClassification,Representative\n"
        "Goldfield Mariners Inc,12 Mabini St,Ermita,Manila,(02) 5550-1,http://x.test,"
        "a@x.test,Valid License,2023-01-19,Manning Agency,Jane Cruz\n",
        encoding="utf-8")
    recs = ik.agency_csv_to_records(str(p))
    assert len(recs) == 1
    r = recs[0]
    assert r["entity_type"] == "recruitment_agency" and r["name"] == "Goldfield Mariners Inc"
    assert r["jurisdiction"] == "PH" and r["status"] == "Valid License"
    assert "Ermita" in r["address"] and "Manila" in r["address"]
    assert r["phones"] == "(02) 5550-1" and r["email"] == "a@x.test"
    assert r["sector"] == "Manning Agency" and r["source_tier"] == "official"
    assert "Jane Cruz" in r["notes"]


def test_joborder_csv_maps_principals_to_employers(tmp_path):
    p = tmp_path / "jo.csv"
    p.write_text(
        "AGENCY,PRINCIPALNAME,JOBSITE,POSITION\n"
        "ABC Manpower,Al Faris Household Services,SAUDI ARABIA,Domestic Worker\n"
        "ABC Manpower,Al Faris Household Services,SAUDI ARABIA,Driver\n"  # dup principal
        "XYZ Crewing,Blue Ocean Shipping,HONG KONG,Seafarer\n",
        encoding="utf-8")
    employers, rels = ik.joborder_csv_to_entities(str(p))
    names = {e["name"]: e for e in employers}
    assert set(names) == {"Al Faris Household Services", "Blue Ocean Shipping"}  # deduped
    assert names["Al Faris Household Services"]["entity_type"] == "employer"
    assert names["Al Faris Household Services"]["jurisdiction"] == "SA"   # jobsite->country code
    assert names["Al Faris Household Services"]["corridor"] == "PH-SA"
    assert names["Blue Ocean Shipping"]["jurisdiction"] == "HK"
    assert len(rels) == 3  # one relationship row per job order


def test_country_code_mapping():
    assert ik._country_code("Saudi Arabia") == "SA"
    assert ik._country_code("HONG KONG") == "HK"
    assert ik._country_code("Taiwan") == "TW"
    assert ik._country_code("Someplace") == "Someplace"  # unknown passes through (truncated)


def test_end_to_end_merge_dedups_agencies_and_employers(tmp_path):
    ag = tmp_path / "ag.csv"
    ag.write_text("Agency,LicenseStatus\nGoldfield Mariners Inc,Valid License\n"
                  "Goldfield Mariners,Cancelled\n", encoding="utf-8")  # same entity, 2 forms
    jo = tmp_path / "jo.csv"
    jo.write_text("AGENCY,PRINCIPALNAME,JOBSITE,POSITION\n"
                  "ABC,Gulf Star LLC,QATAR,Welder\n", encoding="utf-8")
    out = tmp_path / "out.jsonl"
    rc = ik.main(["--agencies", str(ag), "--job-orders", str(jo), "--out", str(out),
                  "--rel-out", str(tmp_path / "rel.jsonl")])
    assert rc == 0
    ekb = _load("entity_kb_for_kaggle_test", _ROOT / "scripts" / "entity_kb.py")
    ents = ekb.load_entities(out)
    by_type = {}
    for e in ents:
        by_type.setdefault(e.entity_type, []).append(e)
    # the two Goldfield agency forms merged into one; the principal became an employer
    assert len(by_type["recruitment_agency"]) == 1
    assert len(by_type["employer"]) == 1 and by_type["employer"][0].jurisdiction == "QA"
