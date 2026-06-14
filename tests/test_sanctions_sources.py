"""Tests for scripts/sanctions_sources.py -- OFAC SDN + World Bank debarred.

Offline: the parsers run against the real on-the-wire formats (OFAC sdn.csv rows,
World Bank SANCTIONED_FIRM JSON); the fetcher is exercised with an injected fetch.
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


ss = _load("sanctions_sources", _ROOT / "scripts" / "sanctions_sources.py")

# real OFAC sdn.csv shape (no header; '-0-' = empty; type '-0-' = entity)
_SDN = ('36,"AEROCARIBBEAN AIRLINES",-0- ,"CUBA",-0- ,-0- ,-0- ,-0- ,-0- ,-0- ,-0- ,-0- \r\n'
        '9639,"HANIYA, Ismail","individual","NS-PLC",-0- ,-0- ,-0- ,-0- ,-0- ,-0- ,-0- ,"DOB 1962."\r\n'
        '555,"SOME TANKER","vessel","IRAN",-0- ,-0- ,"Crude",-0- ,-0- ,-0- ,-0- ,-0- \r\n'
        '173,"ANGLO-CARIBBEAN CO., LTD.",-0- ,"CUBA",-0- ,-0- ,-0- ,-0- ,-0- ,-0- ,-0- ,"Linked to X."\r\n')


def test_parse_sdn_csv_keeps_entities_drops_individuals_and_vessels():
    recs = ss.parse_sdn_csv(_SDN)
    names = {r["name"] for r in recs}
    assert names == {"AEROCARIBBEAN AIRLINES", "ANGLO-CARIBBEAN CO., LTD."}  # entities only
    r = next(r for r in recs if r["name"] == "ANGLO-CARIBBEAN CO., LTD.")
    assert r["entity_type"] == "sanctioned_entity" and r["status"] == "watchlisted"
    assert r["source_tier"] == "official" and "CUBA" in r["notes"] and "Linked to X" in r["notes"]


def test_fetch_ofac_sdn_uses_injected_fetch():
    recs = ss.fetch_ofac_sdn(fetch=lambda url: _SDN)
    assert len(recs) == 2 and all(r["entity_type"] == "sanctioned_entity" for r in recs)


_WB = {"response": [
    {"SUPP_NAME": "ZHONGKE LIFE SCIENCE & TECHNOLOGY CO., LTD.", "SUPP_TYPE_CODE": "F",
     "LAND1": "CN", "COUNTRY_NAME": "China", "SUPP_CITY": "Zhejiang", "SUPP_ADDR": "No. 88 Zhiyuan Rd",
     "DEBAR_FROM_DATE": "2011-07-26", "DEBAR_TO_DATE": "2999-12-31",
     "DEBAR_REASON": "Procurement Guidelines 1.14(a)(ii)"},
    {"SUPP_NAME": "John Doe", "SUPP_TYPE_CODE": "I", "LAND1": "US"},  # individual -> skipped
]}


def test_parse_worldbank_firms_keeps_firms_drops_individuals():
    recs = ss.parse_worldbank_firms(_WB)
    assert len(recs) == 1
    r = recs[0]
    assert r["name"] == "ZHONGKE LIFE SCIENCE & TECHNOLOGY CO., LTD."
    assert r["entity_type"] == "sanctioned_entity" and r["jurisdiction"] == "CN"
    assert r["status"] == "delisted" and r["status_as_of"] == "2011-07-26"
    assert "Zhejiang" in r["address"] and "China" in r["address"]
    assert "Procurement Guidelines" in r["notes"]


def test_find_firm_list_navigates_response_wrapper():
    assert ss._find_firm_list(_WB) is _WB["response"]
    assert ss._find_firm_list({"a": {"b": [{"x": 1}]}}) == [{"x": 1}]
    assert ss._find_firm_list({"empty": {}}) is None
