"""Tests for scripts/openownership_bods.py -- BODS statement parser.

Offline + pure. Fixtures are trimmed from REAL BODS examples
(openownership/data-standard): v0.4 entity/person/relationship records and a legacy
v0.2 entityStatement. Relationships and nameless records must not become entities.
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


b = _load("openownership_bods", _ROOT / "scripts" / "openownership_bods.py")

ENTITY_V04 = {"recordType": "entity", "recordId": "c359f58d2977", "recordStatus": "new",
              "recordDetails": {"entityType": {"type": "registeredEntity"}, "name": "Profitech Ltd",
                                "incorporatedInJurisdiction": {"name": "United Kingdom", "code": "GB"},
                                "identifiers": [{"scheme": "GB-COH", "id": "2063384560"}],
                                "addresses": [{"type": "registered", "address": "42 Example St",
                                               "postCode": "EC1A", "country": "GB"}]}}
PERSON_V04 = {"recordType": "person", "recordId": "10478c6cf6de",
              "recordDetails": {"personType": "knownPerson",
                                "names": [{"type": "legal", "fullName": "Jennifer Hewitson-Smith",
                                           "givenName": "Jennifer", "familyName": "Hewitson-Smith"}],
                                "nationalities": [{"code": "GB", "name": "United Kingdom"}]}}
REL_V04 = {"recordType": "relationship", "recordId": "r1",
           "recordDetails": {"subject": "c359f58d2977", "interestedParty": "10478c6cf6de", "interests": []}}
ENTITY_V02 = {"statementType": "entityStatement", "statementID": "e2", "entityType": "registeredEntity",
              "name": "Old Schema Co", "incorporatedInJurisdiction": {"name": "Kenya", "code": "KE"},
              "identifiers": [{"scheme": "KE-X", "id": "99"}]}


def test_entity_v04_maps_to_company():
    e = b.parse_bods_statement(ENTITY_V04)
    assert e["entity_type"] == "company" and e["name"] == "Profitech Ltd"
    assert e["jurisdiction"] == "GB"
    assert e["license_no"] == "GB-COH:2063384560"
    assert "42 Example St" in e["address"]
    assert e["record_id"] == "c359f58d2977"


def test_person_v04_maps_to_individual():
    e = b.parse_bods_statement(PERSON_V04)
    assert e["entity_type"] == "individual"
    assert e["name"] == "Jennifer Hewitson-Smith"
    assert e["jurisdiction"] == "GB"                      # nationality


def test_relationship_is_not_an_entity():
    assert b.parse_bods_statement(REL_V04) is None


def test_legacy_v02_entity_statement():
    e = b.parse_bods_statement(ENTITY_V02)
    assert e["entity_type"] == "company" and e["name"] == "Old Schema Co"
    assert e["jurisdiction"] == "KE" and e["license_no"] == "KE-X:99"


def test_nameless_entity_skipped():
    assert b.parse_bods_statement({"recordType": "entity", "recordDetails": {"name": ""}}) is None


def test_parse_bods_filters_relationships_and_nameless():
    ents = b.parse_bods([ENTITY_V04, PERSON_V04, REL_V04, {"recordType": "entity", "recordDetails": {}}])
    assert [e["entity_type"] for e in ents] == ["company", "individual"]


def test_iter_statements_handles_array_and_ndjson():
    arr = json.dumps([ENTITY_V04, PERSON_V04])
    ndjson = json.dumps(ENTITY_V04) + "\n" + json.dumps(PERSON_V04)
    assert len(list(b.iter_statements(arr))) == 2
    assert len(list(b.iter_statements(ndjson))) == 2
    assert list(b.iter_statements("  ")) == []
