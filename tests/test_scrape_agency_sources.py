"""Offline tests for the agency-source scraper framework.

Parses synthetic regulator lists (HTML table / JSON / CSV) into normalized
AgencyProfile records and confirms the scraped registry is consumable by the
verifier. No network: --source live paths are tested only for clean
degradation when env config is absent.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = _ROOT / "data" / "agency_registry" / "sample_regulator_list.html"


def _load(rel: str, name: str):
    spec = importlib.util.spec_from_file_location(name, str(_ROOT / rel))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


SC = _load("scripts/scrape_agency_sources.py", "dc_scrape_sources_test")


def test_map_header_heuristics():
    assert SC.map_header("Agency Name") == "name"
    assert SC.map_header("License No.") == "license_no"
    assert SC.map_header("Office Address") == "address"
    assert SC.map_header("Telephone") == "phones"
    assert SC.map_header("Status") == "status"
    assert SC.map_header("totally unrelated column") == ""


def test_parse_html_table_from_fixture():
    recs = SC.parse_html_table(FIXTURE.read_text(encoding="utf-8"))
    assert len(recs) == 4
    by_name = {r["name"]: r for r in recs}
    assert "Sunrise Overseas Manpower Services, Inc." in by_name
    sun = by_name["Sunrise Overseas Manpower Services, Inc."]
    assert sun["license_no"] == "POEA-SAMPLE-1001-LB"
    assert sun["address"] == "Unit 5, Sample Tower, Ermita, Manila"
    assert sun["phones"] == "+63-2-8555-0101"


def test_records_to_profiles_normalizes():
    recs = SC.parse_html_table(FIXTURE.read_text(encoding="utf-8"))
    profiles = SC.records_to_profiles(recs, source="synthetic-html")
    east = next(p for p in profiles if p["name"].startswith("Easternwind"))
    assert east["status"] == "cancelled"               # normalized from "Cancelled"
    assert list(east["phones"]) == ["+63-2-8555-0505"]  # split to a sequence
    assert list(east["job_markets"]) == ["Lebanon"]     # split on ';'
    assert east["official_source"] == "synthetic-html"


def test_scraped_registry_is_usable_by_verifier():
    """A scraped+normalized registry must be directly consumable by the
    licensed-agency verifier -- the whole point of the pipeline."""
    recs = SC.parse_html_table(FIXTURE.read_text(encoding="utf-8"))
    profiles = SC.records_to_profiles(recs, source="synthetic-html")
    reg_mod = _load("scripts/agency_registry.py", "dc_agency_registry_for_scrape_test")
    registry = [reg_mod.profile_from_record(p) for p in profiles]
    v = reg_mod.verify_agency("Easternwind Workforce Solutions", registry)
    assert v.status == "licensed_red" and v.license_status == "cancelled"
    v2 = reg_mod.verify_agency("Sunrise Overseas Manpower Services", registry)
    assert v2.status == "licensed_valid"


def test_parse_json_list_with_path_and_field_mapping():
    payload = {"data": {"records": [
        {"company_name": "Acme Recruitment Inc.", "poea_no": "POEA-X-1",
         "validity": "valid", "contact_no": "+63-2-8555-1111",
         "office_address": "Sample Ave, Manila"},
        {"name": "Beta Manpower", "license": "POEA-X-2", "status": "expired"},
        {"irrelevant_column": "skip"},
    ]}}
    recs = SC.parse_json_list(payload, list_path="data.records")
    assert len(recs) == 2  # the record with no name is dropped
    assert recs[0]["name"] == "Acme Recruitment Inc."
    assert recs[0]["license_no"] == "POEA-X-1"
    assert recs[0]["phones"] == "+63-2-8555-1111"


def test_parse_csv():
    csv_text = ("Agency Name,License No.,Status,Telephone\n"
                "Gamma Services,POEA-Y-9,valid,+63-2-8555-2222\n")
    recs = SC.parse_csv(csv_text)
    assert len(recs) == 1
    assert recs[0]["name"] == "Gamma Services"
    assert recs[0]["phones"] == "+63-2-8555-2222"


def test_scrape_live_degrades_without_env(monkeypatch):
    monkeypatch.delenv("DMW_LIST_URL", raising=False)
    recs, note = SC.scrape_live("dmw_api")
    assert recs == []
    assert "DMW_LIST_URL" in note  # tells the operator exactly what to set


def test_scrape_live_unknown_source():
    recs, note = SC.scrape_live("not_a_source")
    assert recs == [] and "unknown source" in note


def test_cli_from_html(tmp_path):
    out = tmp_path / "scraped.json"
    rc = SC.main(["--from-html", str(FIXTURE), "--out", str(out)])
    assert rc == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["n_records"] == 4
    assert payload["_synthetic"] is False  # it's a parse of real-shaped input
