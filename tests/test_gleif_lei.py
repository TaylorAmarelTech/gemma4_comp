"""Tests for scripts/gleif_lei.py -- GLEIF LEI Records API connector.

Offline: the JSON:API mapping is pure; pagination is exercised through an injected
fetch returning canned pages (the shape mirrors a real api.gleif.org response).
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


g = _load("gleif_lei", _ROOT / "scripts" / "gleif_lei.py")


def _rec(lei="254900N2EEPSHPNU0H50", name="Sailwind Trading FZE"):
    return {"type": "lei-records", "id": lei, "attributes": {
        "lei": lei,
        "entity": {"legalName": {"name": name, "language": "en"},
                   "otherNames": [{"name": "Sailwind", "language": "en"}],
                   "legalAddress": {"addressLines": ["Unit 3303", "DMCC Business Centre"],
                                    "city": "Dubai", "country": "AE", "postalCode": "00000"},
                   "jurisdiction": "AE", "legalForm": {"id": "8888"}, "status": "ACTIVE"},
        "registration": {"status": "ISSUED"}}}


def _page(recs, *, last):
    return {"meta": {"pagination": {"currentPage": 1, "perPage": 200, "total": 99, "lastPage": last}},
            "data": recs}


def test_parse_lei_record_maps_fields():
    e = g.parse_lei_record(_rec())
    assert e["name"] == "Sailwind Trading FZE"
    assert e["lei"] == "254900N2EEPSHPNU0H50"
    assert e["entity_type"] == "company" and e["jurisdiction"] == "AE"
    assert e["status"] == "ISSUED"                       # registration status
    assert "Dubai" in e["address"] and "AE" in e["address"]
    assert e["aliases"] == ["Sailwind"]


def test_parse_lei_record_skips_nameless():
    bad = {"attributes": {"lei": "X", "entity": {"legalName": {"name": ""}}}}
    assert g.parse_lei_record(bad) is None


def test_build_url_has_bracketed_params():
    url = g.build_url(country="ae", page=2, page_size=50)
    assert "page%5Bsize%5D=50" in url and "page%5Bnumber%5D=2" in url
    assert "filter%5Bentity.legalAddress.country%5D=AE" in url   # uppercased


def test_fetch_paginates_until_last_page():
    calls = {"n": 0}
    def fetch(url):
        calls["n"] += 1
        return _page([_rec(name=f"Co {calls['n']}A"), _rec(name=f"Co {calls['n']}B")],
                     last=2)               # two pages available
    ents = g.fetch_lei_records(country="AE", limit=100, fetch=fetch)
    assert calls["n"] == 2 and len(ents) == 4            # both pages pulled, then stops at lastPage


def test_fetch_respects_limit():
    def fetch(url):
        return _page([_rec(name=f"Co {i}") for i in range(200)], last=10)
    ents = g.fetch_lei_records(country="AE", limit=3, fetch=fetch)
    assert len(ents) == 3                                # capped, no runaway crawl
