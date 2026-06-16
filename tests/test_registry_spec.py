"""Tests for scripts/registry_spec.py -- the config-driven resolver engine.

Offline: parse_spec dispatch + to_entities stamping + resolve-with-injected-fetch
are exercised on inline content; load_specs/validate_spec run against the shipped
registry_specs.yaml.
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


rs = _load("registry_spec", _ROOT / "scripts" / "registry_spec.py")


# ---- parse_spec dispatch --------------------------------------------------

def test_parse_spec_html_table():
    spec = {"format": "html_table", "fields": {"name": "Name", "status": "Status"}}
    html = "<table><tr><th>Name</th><th>Status</th></tr><tr><td>Acme</td><td>Active</td></tr></table>"
    assert rs.parse_spec(spec, html) == [{"name": "Acme", "status": "Active"}]


def test_parse_spec_json_accepts_text_or_object():
    spec = {"format": "json", "fields": {"name": "n"}}
    assert rs.parse_spec(spec, [{"n": "Alpha"}]) == [{"name": "Alpha"}]
    assert rs.parse_spec(spec, '[{"n": "Beta"}]') == [{"name": "Beta"}]


def test_parse_spec_index_mode_with_filter():
    spec = {"format": "html_table", "fields": {"rank": 0, "name": 1, "score": 2},
            "row_filter": {"field": "rank", "pattern": r"^\d+$"}}
    html = ("<table><tr><td>序号</td><td>名称</td><td>得分</td></tr>"
            "<tr><td>1</td><td>Ent A</td><td>117</td></tr></table>")
    recs = rs.parse_spec(spec, html)
    assert recs == [{"rank": "1", "name": "Ent A", "score": "117"}]


def test_parse_spec_unknown_format_raises():
    try:
        rs.parse_spec({"format": "xml", "fields": {}}, "x")
        assert False
    except ValueError:
        pass


# ---- to_entities ----------------------------------------------------------

def test_to_entities_stamps_metadata_and_notes():
    spec = {"entity_type": "lender", "jurisdiction": "BD", "default_status": "licensed",
            "note_fields": ["score"], "source": "BD MRA"}
    ents = rs.to_entities([{"name": "Alpha MFI", "license_no": "001", "score": "117"}], spec)
    e = ents[0]
    assert e["entity_type"] == "lender" and e["jurisdiction"] == "BD"
    assert e["status"] == "licensed" and e["source"] == "BD MRA" and e["source_tier"] == "official"
    assert "License 001" in e["notes"] and "score: 117" in e["notes"]


def test_to_entities_prefers_record_status_over_default():
    spec = {"entity_type": "recruitment_agency", "jurisdiction": "PH", "default_status": "licensed"}
    ents = rs.to_entities([{"name": "X", "status": "Cancelled"}], spec)
    assert ents[0]["status"] == "Cancelled"


def test_to_entities_drops_nameless():
    ents = rs.to_entities([{"name": ""}, {"name": "Keep"}], {"entity_type": "company"})
    assert len(ents) == 1 and ents[0]["name"] == "Keep"


# ---- resolve with injected fetch ------------------------------------------

def test_resolve_pipes_fetch_through_to_entities():
    spec = {"url": "https://x/api", "format": "json", "entity_type": "lender",
            "jurisdiction": "BD", "fields": {"name": "full", "license_no": "lic"}}
    calls = []

    def fetch(url, binary):
        calls.append((url, binary))
        return '[{"full": "Alpha MFI", "lic": "001"}]'
    ents = rs.resolve(spec, fetch=fetch)
    assert calls == [("https://x/api", False)]   # json -> text fetch
    assert ents[0]["name"] == "Alpha MFI" and ents[0]["entity_type"] == "lender"


def test_resolve_paginates_offset_style():
    spec = {"url": "https://x/api?resource_id=r", "format": "json", "entity_type": "company",
            "fields": {"name": "n"}, "list_path": "result.records",
            "paginate": {"size_param": "limit", "offset_param": "offset", "size": 2, "max_records": 10}}
    pages = {0: '{"result":{"records":[{"n":"A"},{"n":"B"}]}}',
             2: '{"result":{"records":[{"n":"C"}]}}'}      # partial page -> stop
    urls = []

    def fetch(url, binary):
        urls.append(url)
        off = int(url.split("offset=")[1])
        return pages.get(off, '{"result":{"records":[]}}')
    ents = rs.resolve(spec, fetch=fetch)
    assert [e["name"] for e in ents] == ["A", "B", "C"]
    assert "limit=2&offset=0" in urls[0] and "offset=2" in urls[1]


def test_resolve_requests_binary_for_xlsx():
    spec = {"url": "https://x.xlsx", "format": "xlsx", "entity_type": "company",
            "fields": {"name": "Name"}}
    seen = {}

    def fetch(url, binary):
        seen["binary"] = binary
        raise RuntimeError("stop after fetch")  # we only assert the binary flag
    try:
        rs.resolve(spec, fetch=fetch)
    except RuntimeError:
        pass
    assert seen["binary"] is True


# ---- the shipped spec catalogue -------------------------------------------

def test_shipped_specs_load_and_validate():
    specs = rs.load_specs()
    assert {"bd_oep_cfg", "bd_mra_cfg", "cn_mara_cfg"} <= set(specs)
    for sid, spec in specs.items():
        assert rs.validate_spec(spec) == [], f"{sid}: {rs.validate_spec(spec)}"


def test_validate_spec_catches_problems():
    assert "missing url" in rs.validate_spec({"id": "x", "format": "json", "entity_type": "c",
                                              "fields": {"name": "n"}})
    assert any("format" in p for p in rs.validate_spec(
        {"id": "x", "url": "u", "format": "toml", "entity_type": "c", "fields": {"n": 1}}))
