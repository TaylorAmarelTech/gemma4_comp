"""Tests for scripts/bd_mra_mfi.py -- BD MRA licensed-MFI JSON parse.

Offline: the parser runs against the REAL mfi-list JSON shape (synthetic MFI
names); download is exercised through an injected fetch.
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


mra = _load("bd_mra_mfi", _ROOT / "scripts" / "bd_mra_mfi.py")

# real field names, synthetic orgs
_JSON = [
    {"license_no": "00001", "short_name_of_org": "SNF", "full_name_of_org": "Sample Niloy Foundation",
     "full_name_of_org_in_bengali": "নমুনা", "address_of_org": "22/A Sample Sarak, Jashore",
     "license_issue_date": "2007-09-05", "licensing_year": "2007",
     "email_address": "sample@example.org", "licensing_state_id": "30"},
    {"license_no": "00777", "short_name_of_org": "SCM", "full_name_of_org": "Sample Credit Mission",
     "full_name_of_org_in_bengali": "", "address_of_org": "Dhaka",
     "license_issue_date": "2012-01-10", "licensing_year": "2012",
     "email_address": "", "licensing_state_id": "130"},
    {"license_no": "00999", "short_name_of_org": "", "full_name_of_org": "",  # no name -> dropped
     "address_of_org": "Nowhere", "licensing_state_id": "30"},
]


def test_parse_drops_nameless_and_keeps_rest():
    recs = mra.parse_mfi_json(_JSON)
    assert len(recs) == 2


def test_parse_fields():
    r = mra.parse_mfi_json(_JSON)[0]
    assert r["name"] == "Sample Niloy Foundation" and r["license_no"] == "00001"
    assert r["license_issue_date"] == "2007-09-05" and r["state_id"] == "30"
    assert r["jurisdiction"] == "BD" and r["source_tier"] == "official"
    assert r["status"] == "licensed"  # never asserts active/cancelled it can't verify


def test_items_unwraps_dict_payloads():
    assert mra._items({"data": [{"full_name_of_org": "X"}]}) == [{"full_name_of_org": "X"}]
    assert mra._items([{"a": 1}]) == [{"a": 1}]
    assert mra._items({"nope": 5}) == []


def test_records_to_entities_are_bd_lenders_with_state_in_notes():
    ents = mra.records_to_entities(mra.parse_mfi_json(_JSON))
    assert all(e["entity_type"] == "lender" and e["jurisdiction"] == "BD" for e in ents)
    e0 = ents[0]
    assert "00001" in e0["notes"] and "MRA state 30" in e0["notes"]
    assert "2007-09-05" in e0["notes"]


def test_download_json_uses_injected_fetch_str_or_obj():
    calls = []
    out = mra.download_json(fetch=lambda u: calls.append(u) or json.dumps(_JSON))
    assert calls == [mra.MRA_URL] and len(mra.parse_mfi_json(out)) == 2
    # also accepts an already-parsed object
    assert mra.download_json(fetch=lambda u: _JSON) == _JSON


def test_empty_payload_yields_no_records():
    assert mra.parse_mfi_json([]) == [] and mra.parse_mfi_json({}) == []
