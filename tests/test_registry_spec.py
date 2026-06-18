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


# ---- link discovery -------------------------------------------------------

def test_discover_url_picks_latest_dated_link():
    page = ('<a href="https://x/data_2026-01-01.csv">old</a>'
            '<a href="https://x/data_2026-06-15.csv">new</a>')
    url = rs.discover_url({"page": "https://site/reg", "link_pattern": r"\.csv", "pick": "latest"},
                          fetch=lambda u, b: page)
    assert url == "https://x/data_2026-06-15.csv"


def test_discover_url_absolutizes_relative_href():
    page = '<a href="/media/abc/list-15.06.2026.xlsx">x</a>'
    url = rs.discover_url({"page": "https://amsa.gov.au/ships", "link_pattern": r"\.xlsx"},
                          fetch=lambda u, b: page)
    assert url == "https://amsa.gov.au/media/abc/list-15.06.2026.xlsx"


def test_discover_url_ckan_resources():
    pkg = ('{"result":{"resources":['
           '{"url":"https://o/positive_en.csv","name":"positive en","format":"CSV"},'
           '{"url":"https://o/positive_fr.csv","name":"positive fr","format":"CSV"}]}}')
    url = rs.discover_url({"page": "https://ckan/api", "format": "ckan",
                          "link_pattern": "positive_en"}, fetch=lambda u, b: pkg)
    assert url == "https://o/positive_en.csv"


def test_discover_url_raises_when_no_match():
    try:
        rs.discover_url({"page": "p", "link_pattern": r"\.csv"}, fetch=lambda u, b: "<html>no links</html>")
        assert False
    except ValueError:
        pass


def test_date_key_parses_formats():
    assert rs._date_key("x_2026-06-15.csv") == (2026, 6, 15)
    assert rs._date_key("list-15.06.2026.xlsx") == (2026, 6, 15)
    assert rs._date_key("nope.csv") == (0, 0, 0)


def test_date_key_quarter_token():
    assert rs._date_key("tfwp_2020q3_positive_en.csv") == (2020, 9, 0)
    assert rs._date_key("2020q3") > rs._date_key("2020q1") > rs._date_key("2019q4")


def test_discover_ckan_picks_latest_quarter_by_name_not_upload_time():
    # all resources share a last_modified; the period lives in the URL/name -> quarter wins
    pkg = ('{"result":{"resources":['
           '{"url":"https://o/tfwp_2019q4_positive_en.csv","name":"2019Q4","last_modified":"2022-02-10"},'
           '{"url":"https://o/tfwp_2020q3_positive_en.csv","name":"2020Q3","last_modified":"2022-02-10"}]}}')
    url = rs.discover_url({"page": "p", "format": "ckan", "link_pattern": r"positive_en\.csv"},
                         fetch=lambda u, b: pkg)
    assert url.endswith("tfwp_2020q3_positive_en.csv")


def test_resolve_with_discover_then_fetches_data():
    spec = {"format": "csv", "entity_type": "company", "jurisdiction": "GB",
            "fields": {"name": "Name"},
            "discover": {"page": "https://gov.uk/reg", "link_pattern": r"\.csv", "pick": "latest"}}

    def fetch(url, binary):
        if url == "https://gov.uk/reg":
            return ('<a href="https://x/data_2026-01-01.csv">old</a>'
                    '<a href="https://x/data_2026-06-15.csv">new</a>')
        if url == "https://x/data_2026-06-15.csv":
            return "Name\nAcme Sample Ltd\n"
        return ""
    ents = rs.resolve(spec, fetch=fetch)
    assert [e["name"] for e in ents] == ["Acme Sample Ltd"]   # discovered latest, then parsed


def _boom(url, binary):
    raise OSError("blocked")


def test_default_fetch_uses_urllib_when_it_works(monkeypatch):
    monkeypatch.setattr(rs, "_urllib_fetch", lambda u, b: "VIA_URLLIB")
    monkeypatch.setattr(rs, "_curl_fetch", lambda u, b: "VIA_CURL")
    assert rs._default_fetch("https://x", False) == "VIA_URLLIB"


def test_default_fetch_falls_back_to_curl_on_failure(monkeypatch):
    monkeypatch.setattr(rs, "_urllib_fetch", _boom)
    monkeypatch.setattr(rs, "_curl_fetch", lambda u, b: "VIA_CURL")
    assert rs._default_fetch("https://x", False) == "VIA_CURL"   # urllib blocked -> curl_cffi


def test_validate_spec_accepts_discover_without_url():
    spec = {"id": "x", "format": "csv", "entity_type": "company", "fields": {"name": "N"},
            "discover": {"page": "https://p", "link_pattern": r"\.csv"}}
    assert rs.validate_spec(spec) == []
    # but a spec with neither url nor discover.page is invalid
    assert any("url or discover" in p for p in rs.validate_spec(
        {"id": "x", "format": "csv", "entity_type": "company", "fields": {"name": "N"}}))


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
    assert any("url" in p for p in rs.validate_spec({"id": "x", "format": "json", "entity_type": "c",
                                                     "fields": {"name": "n"}}))
    assert any("format" in p for p in rs.validate_spec(
        {"id": "x", "url": "u", "format": "toml", "entity_type": "c", "fields": {"n": 1}}))
