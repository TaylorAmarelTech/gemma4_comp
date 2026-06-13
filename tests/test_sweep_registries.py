"""Tests for scripts/sweep_registries.py -- the catalogued-registry sweep.

Fully offline: the connector's renderer is injectable, so candidate selection,
the per-registry classification (extracted / endpoint_only / no_data / error),
and matrix aggregation are tested with a fake renderer -- no browser, no network.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


sw = _load("sweep_registries", _ROOT / "scripts" / "sweep_registries.py")
bs = _load("browser_scrape_for_sweep_test", _ROOT / "scripts" / "browser_scrape.py")

_SOURCES = [
    {"id": "bd_oep", "url": "https://oep.gov.bd/agencies", "official": True,
     "access_tier": "free", "entity_types": ["recruitment_agency"]},
    {"id": "dmw_inquiry", "url": "https://dmw.gov.ph/inquiry/licensed-recruitment-agencies",
     "official": True, "access_tier": "free", "entity_types": ["recruitment_agency"]},  # excluded (done)
    {"id": "clinic_pdf", "url": "https://x.gov/clinics.pdf", "official": True,
     "access_tier": "free", "entity_types": ["medical_clinic"]},  # excluded (pdf)
    {"id": "companies_house", "url": "https://find.company-information.service.gov.uk",
     "official": True, "access_tier": "freemium", "entity_types": ["employer"]},  # excluded (freemium)
    {"id": "ngo_portal", "url": "https://ngo.example.org", "official": False,
     "access_tier": "free", "entity_types": ["ngo"]},  # excluded (not official, no agency entity)
    {"id": "tw_wda", "url": "https://agent.wda.gov.tw/agentext/", "official": True,
     "access_tier": "free", "entity_types": ["recruitment_agency", "broker"]},
]


def test_select_candidates_filters_to_official_fetchable_agency_registries():
    cand_ids = {c["id"] for c in sw.select_candidates(_SOURCES)}
    assert cand_ids == {"bd_oep", "tw_wda"}  # excludes done/pdf/freemium/non-official


def test_select_candidates_by_explicit_ids_overrides_filters():
    cand = sw.select_candidates(_SOURCES, ids={"companies_house", "dmw_inquiry"})
    assert {c["id"] for c in cand} == {"companies_house", "dmw_inquiry"}


def test_classify_status():
    assert sw._classify(0, 0, "Boom") == "error"
    assert sw._classify(3, 5, "") == "extracted"
    assert sw._classify(3, 0, "") == "endpoint_only"
    assert sw._classify(0, 0, "") == "no_data"


def _dmw_payload():
    return json.dumps({"meta": {"lastPage": 1}, "data": [
        {"name": "Acme Manpower", "classification": "Private Employment Agency",
         "license_status": "Valid License", "is_valid": True}]})


def test_sweep_classifies_each_registry_from_renderer_output():
    cands = [{"id": "extract_me", "url": "https://a.test"},
             {"id": "endpoint_only", "url": "https://b.test"},
             {"id": "no_data", "url": "https://c.test"},
             {"id": "boom", "url": "https://d.test"}]

    def fake_renderer(cfg):
        if cfg.label == "extract_me":
            return bs.CaptureResult(payloads=[{"url": cfg.url + "/api/licensed-agencies?page=1",
                                               "text": _dmw_payload()}],
                                    discovered_endpoints=[cfg.url + "/api/licensed-agencies?page=1"])
        if cfg.label == "endpoint_only":
            return bs.CaptureResult(payloads=[{"url": cfg.url + "/api/config", "text": '{"build":"x"}'}],
                                    discovered_endpoints=[cfg.url + "/api/config"])
        if cfg.label == "no_data":
            return bs.CaptureResult(payloads=[], discovered_endpoints=[])
        raise RuntimeError("render crashed")

    results = sw.sweep(cands, renderer=fake_renderer)
    by_id = {r["id"]: r for r in results}
    assert by_id["extract_me"]["status"] == "extracted"
    assert by_id["extract_me"]["n_records"] == 1
    assert "licensed-agencies" in by_id["extract_me"]["agency_endpoint"]
    assert by_id["endpoint_only"]["status"] == "endpoint_only"
    assert by_id["endpoint_only"]["n_records"] == 0 and by_id["endpoint_only"]["n_endpoints"] == 1
    assert by_id["no_data"]["status"] == "no_data"
    assert by_id["boom"]["status"] == "error" and "RuntimeError" in by_id["boom"]["error"]


def test_sweep_surfaces_pagination_page_count():
    cands = [{"id": "paged", "url": "https://p.test"}]
    payload = json.dumps({"meta": {"lastPage": 76}, "data": [
        {"name": "X", "license_status": "Valid License", "classification": "PEA", "is_valid": True}]})

    def fake_renderer(cfg):
        return bs.CaptureResult(payloads=[{"url": cfg.url + "/licensed-agencies?page=1", "text": payload}],
                                discovered_endpoints=[cfg.url + "/licensed-agencies?page=1"])

    row = sw.sweep(cands, renderer=fake_renderer)[0]
    assert row["last_page"] == 76 and row["status"] == "extracted"
