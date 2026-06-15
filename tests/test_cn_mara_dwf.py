"""Tests for scripts/cn_mara_dwf.py -- CN MARA distant-water-fishing compliance parse.

Offline: the parser runs against the real notice table layout (rank | enterprise
name | score) with synthetic names; download exercised via an injected fetch.
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


mara = _load("cn_mara_dwf", _ROOT / "scripts" / "cn_mara_dwf.py")

# real layout: header row then rank/name/score rows, with &nbsp; padding
_HTML = """
<table><tbody>
  <tr><td>序号&nbsp;</td><td>企业名称&nbsp;</td><td>得分&nbsp;</td></tr>
  <tr><td>1&nbsp;</td><td>Sample Ocean Foods Co Ltd&nbsp;</td><td>117&nbsp;</td></tr>
  <tr><td>2&nbsp;</td><td>Sample Distant Fishing Ltd&nbsp;</td><td>108&nbsp;</td></tr>
  <tr><td>3&nbsp;</td><td>Sample Half Point Co&nbsp;</td><td>109.5&nbsp;</td></tr>
  <tr><td>4&nbsp;</td><td>Sample Low Score Marine Co&nbsp;</td><td>89&nbsp;</td></tr>
</tbody></table>
<tr><td>note</td><td>not a row</td></tr>
"""


def test_parse_skips_header_and_chrome():
    recs = mara.parse_mara_html(_HTML)
    assert len(recs) == 4


def test_decimal_score_is_parsed():
    # real scores include half-points (e.g. 109.5) -- must not be dropped
    r = next(x for x in mara.parse_mara_html(_HTML) if x["rank"] == 3)
    assert r["score"] == 109.5
    e = next(e for e in mara.records_to_entities(mara.parse_mara_html(_HTML)) if "rank 3/" in e["notes"])
    assert "score 109.5" in e["notes"]


def test_parse_fields():
    r = mara.parse_mara_html(_HTML)[0]
    assert r["rank"] == 1 and r["name"] == "Sample Ocean Foods Co Ltd" and r["score"] == 117
    assert r["jurisdiction"] == "CN" and r["source_tier"] == "official"


def test_low_score_enterprise_captured():
    r = next(x for x in mara.parse_mara_html(_HTML) if x["rank"] == 4)
    assert r["score"] == 89  # the worst-compliance / highest-risk enterprise


def test_records_to_entities_put_score_and_rank_in_notes():
    ents = mara.records_to_entities(mara.parse_mara_html(_HTML))
    assert all(e["entity_type"] == "company" and e["jurisdiction"] == "CN" for e in ents)
    e0 = ents[0]
    assert "score 117" in e0["notes"] and "rank 1/4" in e0["notes"]
    assert e0["sector"] == "distant_water_fishing"


def test_download_uses_injected_fetch():
    calls = []
    out = mara.download_html(fetch=lambda u: calls.append(u) or _HTML)
    assert calls == [mara.MARA_URL] and len(mara.parse_mara_html(out)) == 4


def test_empty_html_yields_no_records():
    assert mara.parse_mara_html("") == []
