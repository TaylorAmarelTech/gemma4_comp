"""Tests for scripts/bd_oep_agencies.py -- BD OEP recruiting-agency HTML parse.

Offline: the parser runs against the REAL OEP table structure (7 columns,
licence-number-led data rows) with synthetic agency names; download is exercised
through an injected fetch.
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


oep = _load("bd_oep_agencies", _ROOT / "scripts" / "bd_oep_agencies.py")

# real column layout: # | License No | Agent Name | Address | Office Phone | Status | Validity
_HTML = """
<table id="agencies"><thead>
  <tr><th>#SL</th><th>License No</th><th>Agent Name</th><th>Address</th>
      <th>Office Phone</th><th>License Status</th><th>License Validity Date</th></tr>
</thead><tbody>
  <tr><td>1</td><td>RL1857</td><td>Sample Plus Overseas Limited</td><td>Dhaka</td>
      <td>+880248810030</td><td>Active</td><td>2027-01-15</td></tr>
  <tr><td>2</td><td>RL2058</td><td>Sample Job Wheels</td><td>Chattogram</td>
      <td>+8801719856955</td><td>Expired</td><td>2024-06-30</td></tr>
  <tr><td>3</td><td>RL0099</td><td>Sample Cancelled Recruiters &amp; Co</td><td>Sylhet</td>
      <td>01710704334</td><td>Cancelled</td><td>2023-03-01</td></tr>
</tbody></table>
<tr><td>note</td><td>not a licence</td><td>chrome row</td></tr>
"""


def test_parses_all_data_rows_skips_header_and_chrome():
    recs = oep.parse_oep_html(_HTML)
    assert len(recs) == 3  # header (th) + the non-licence chrome row excluded


def test_row_fields():
    r = oep.parse_oep_html(_HTML)[0]
    assert r["license_no"] == "RL1857" and r["name"] == "Sample Plus Overseas Limited"
    assert r["address"] == "Dhaka" and r["phone"] == "+880248810030"
    assert r["status"] == "Active" and r["license_validity"] == "2027-01-15"
    assert r["jurisdiction"] == "BD" and r["source_tier"] == "official"


def test_html_entities_unescaped():
    r = next(x for x in oep.parse_oep_html(_HTML) if x["license_no"] == "RL0099")
    assert r["name"] == "Sample Cancelled Recruiters & Co" and r["status"] == "Cancelled"


def test_records_to_entities_are_bd_recruiters():
    ents = oep.records_to_entities(oep.parse_oep_html(_HTML))
    assert ents and all(e["entity_type"] == "recruitment_agency" and e["jurisdiction"] == "BD"
                        for e in ents)
    e0 = ents[0]
    assert e0["license_no"] == "RL1857" and "RL1857" in e0["notes"]
    assert e0["phones"] == "+880248810030"


def test_status_preserved_for_watchlist():
    statuses = {r["status"] for r in oep.parse_oep_html(_HTML)}
    assert {"Active", "Expired", "Cancelled"} <= statuses


def test_download_uses_injected_fetch():
    calls = []
    out = oep.download_html(fetch=lambda u: calls.append(u) or _HTML)
    assert calls == [oep.OEP_URL] and oep.parse_oep_html(out)


def test_empty_html_yields_no_records():
    assert oep.parse_oep_html("") == []
