"""Tests for scripts/gleif_rr.py -- GLEIF Level-2 parent/child relationship edges.

Offline: the RR->edge mapping is pure; fetching is exercised through an injected fetch.
The fixture mirrors a real api.gleif.org relationship-record (captured 2026-06-19).
"""
from __future__ import annotations

import copy
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


rr = _load("gleif_rr", _ROOT / "scripts" / "gleif_rr.py")

RR_DIRECT = {"data": {"type": "relationship-records", "attributes": {
    "relationship": {
        "startNode": {"id": "254900TF64ASRE9OIT26", "type": "LEI"},   # child
        "endNode": {"id": "2549007PTYZFNYSP7208", "type": "LEI"},     # parent
        "type": "IS_DIRECTLY_CONSOLIDATED_BY", "status": "ACTIVE",
        "periods": [{"startDate": "1972-02-28T00:00:00Z", "type": "RELATIONSHIP_PERIOD"},
                    {"startDate": "2025-01-01T00:00:00Z", "endDate": "2025-12-31T00:00:00Z",
                     "type": "ACCOUNTING_PERIOD"}]}}}}


def test_parse_rr_direct_parent_edge():
    e = rr.parse_rr_record(RR_DIRECT)
    assert e["subject_id"] == "2549007PTYZFNYSP7208"     # parent = endNode
    assert e["object_id"] == "254900TF64ASRE9OIT26"      # child = startNode
    assert e["predicate"] == "parent_of" and e["weight"] == 0.95
    assert e["qualifier"]["rel_type"] == "direct"
    assert e["qualifier"]["status"] == "ACTIVE"
    assert e["qualifier"]["start_date"] == "1972-02-28"   # RELATIONSHIP_PERIOD, date-only


def test_parse_rr_ultimate_lower_weight():
    payload = copy.deepcopy(RR_DIRECT)
    payload["data"]["attributes"]["relationship"]["type"] = "IS_ULTIMATELY_CONSOLIDATED_BY"
    e = rr.parse_rr_record(payload)
    assert e["weight"] == 0.9 and e["qualifier"]["rel_type"] == "ultimate"


def test_parse_rr_none_when_no_relationship():
    assert rr.parse_rr_record({"data": {"attributes": {}}}) is None
    assert rr.parse_rr_record({}) is None
    assert rr.parse_rr_record({"data": {"attributes": {"relationship":
                                                       {"startNode": {"id": "X"}}}}}) is None  # no parent


def test_rr_url():
    assert rr.rr_url("ABC", "direct").endswith("/lei-records/ABC/direct-parent-relationship")
    assert rr.rr_url("ABC", "ultimate").endswith("/lei-records/ABC/ultimate-parent-relationship")


def test_fetch_parent_edges_dedups_and_skips_no_parent():
    def fetch(url):
        if "direct" in url:
            return RR_DIRECT                              # both LEIs' direct -> same edge
        raise RuntimeError("404 no ultimate parent")      # ultimate -> reporting-exception
    edges = rr.fetch_parent_edges(["X", "Y"], fetch=fetch)
    assert len(edges) == 1                                # deduped (same parent,child,direct)
    assert edges[0]["subject_id"] == "2549007PTYZFNYSP7208"
