"""Tests for scripts/doj_press.py -- DOJ press-release -> prosecution document.

Offline + pure: the parse/extract helpers run on a fixture mirroring a real
justice.gov/api/v1/press_releases.json record; pagination uses an injected fetch.
"""
from __future__ import annotations

import importlib.util
import sys
import urllib.parse
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


dp = _load("doj_press", _ROOT / "scripts" / "doj_press.py")

REC = {"title": "Member of Human Trafficking Ring Pleads Guilty",
       "body": "<p>A man pleaded guilty to forced labor in violation of "
               "<b>18 U.S.C. &sect; 1589</b> and 18 U.S.C. 1590.</p>",
       "date": "1738777030", "number": "24-1234",
       "component": [{"uuid": "x", "name": "Civil Rights Division"},
                     {"uuid": "y", "name": "USAO - Southern District of Texas"}],
       "teaser": "<p>Guilty plea.</p>", "url": "https://www.justice.gov/opa/pr/x", "uuid": "abc"}


def test_parse_release_structures_and_extracts():
    d = dp.parse_release(REC)
    assert d["date"] == "2025-02-05"                                  # unix ts -> ISO date
    assert "Civil Rights Division" in d["office"] and "Southern District of Texas" in d["office"]
    assert d["statutes"] == ["18 USC 1589", "18 USC 1590"]            # both citations, deduped
    assert "forced labor" in d["offenses"] and "human trafficking" in d["offenses"]  # plain-language tag
    assert "<" not in d["text"] and "forced labor" in d["text"]      # HTML stripped
    assert d["pr_number"] == "24-1234" and d["source"].startswith("DOJ")


def test_offenses_tags_plain_language_charges():
    o = dp.offenses("charged with conspiracy to commit wire fraud and forced labor")
    assert "forced labor" in o and "wire fraud" in o and "conspiracy" in o
    assert dp.offenses("a routine appointment announcement") == []


def test_strip_html_unescapes_and_strips():
    assert dp._strip_html("<p>a &amp; b</p>") == "a & b"


def test_ts_to_iso():
    assert dp._ts_to_iso("1738777030") == "2025-02-05"
    assert dp._ts_to_iso("not-a-number") == ""


def test_statutes_dedups_and_normalizes():
    s = dp.statutes("violated Title 18 U.S.C. § 1591, also 18 USC 1591 and 8 U.S.C. 1324")
    assert s == ["18 USC 1591", "8 USC 1324"]                         # 1591 deduped, order preserved


def test_select_filters_on_title_and_text():
    recs = [{"title": "forced labor case", "text": "18 USC 1589"},
            {"title": "drug case", "text": "narcotics"}]
    out = dp.select(recs, "1589|forced labor")
    assert len(out) == 1 and out[0]["title"] == "forced labor case"


def test_build_url_has_filter_sort_and_paging():
    u = dp.build_url(title="human trafficking", page=2, pagesize=50)
    assert "title=human+trafficking" in u and "page=2" in u
    assert "pagesize=50" in u and "direction=DESC" in u


def test_fetch_releases_paginates_and_caps():
    def fetch(url):
        page = int(urllib.parse.parse_qs(urllib.parse.urlparse(url).query)["page"][0])
        return {"results": [dict(REC, title=f"r{page}-{i}") for i in range(50)]}
    docs = dp.fetch_releases(max_records=120, pagesize=50, fetch=fetch)
    assert len(docs) == 120                                           # 50 + 50 + 20, capped
