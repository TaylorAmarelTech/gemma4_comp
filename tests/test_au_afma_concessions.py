"""Tests for scripts/au_afma_concessions.py -- AFMA concession-holder XLSX collector.

Offline: link cleaning and the row interpreter are pure functions; the stdlib
XLSX reader is exercised against an in-memory workbook; download is injected.
"""
from __future__ import annotations

import importlib.util
import io
import sys
import zipfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


afma = _load("au_afma_concessions", _ROOT / "scripts" / "au_afma_concessions.py")

_NS = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'


def _xlsx(shared, rows_xml):
    sst = f"<sst {_NS}>" + "".join(f"<si><t>{s}</t></si>" for s in shared) + "</sst>"
    sheet = f"<worksheet {_NS}><sheetData>{rows_xml}</sheetData></worksheet>"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("xl/sharedStrings.xml", sst)
        z.writestr("xl/worksheets/sheet1.xml", sheet)
    return buf.getvalue()


# ---- link cleaning --------------------------------------------------------

def test_clean_url_fixes_doubled_prefix_and_trailing_garbage():
    bad = "https://www.afma.gov.ahttps://www.afma.gov.au/sites/x/npf_1_may_2026.xlsxu/sites/x.xlsx"
    assert afma._clean_url(bad) == "https://www.afma.gov.au/sites/x/npf_1_may_2026.xlsx"
    assert afma._clean_url("/sites/x/coral_2_march_2026.xlsx") == \
        "https://www.afma.gov.au/sites/x/coral_2_march_2026.xlsx"


def test_clean_xlsx_links_keeps_latest_per_fishery():
    html = ('<a href="/sites/default/files/2026-03/northern_prawn_fishery_2_march_2026.xlsx">a</a>'
            '<a href="/sites/default/files/2026-06/northern_prawn_fishery_2_june_2026.xlsx">b</a>'
            '<a href="/sites/default/files/2026-05/coral_sea_fishery_permits_1_may_2026.xlsx">c</a>')
    links = afma.clean_xlsx_links(html)
    assert len(links) == 2                                   # two distinct fisheries
    npf = [l for l in links if "northern_prawn" in l][0]
    assert "2026-06" in npf                                   # latest month wins


# ---- xlsx reader ----------------------------------------------------------

def test_read_xlsx_resolves_shared_strings_and_numbers():
    shared = ["Owner Name", "Operational Status", "Permit Number", "ACME Sample Pty Ltd", "Current"]
    rows_xml = (
        '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c>'
        '<c r="C1" t="s"><v>2</v></c></row>'
        '<row r="2"><c r="A2" t="s"><v>3</v></c><c r="B2" t="s"><v>4</v></c>'
        '<c r="C2"><v>1005612</v></c></row>'
    )
    rows = afma.read_xlsx(_xlsx(shared, rows_xml))
    assert rows[0] == ["Owner Name", "Operational Status", "Permit Number"]
    assert rows[1] == ["ACME Sample Pty Ltd", "Current", "1005612"]


# ---- row interpretation ---------------------------------------------------

_ROWS = [
    ["NORTHERN PRAWN FISHERY CARRIER PERMITS - 2 JUNE 2026", "", "", ""],
    ["Owner Name", "Fishery", "Operational Status", "Permit Number"],
    ["Australia Sample Seafoods Pty Ltd", "NPF Fishery", "Current", "1005612"],
    ["Sample Fishing Licences Pty Ltd", "NPF Fishery", "Current", "1005615"],
    ["", "", "", ""],  # blank -> skipped
]


def test_parse_holder_rows_detects_header_and_maps_columns():
    recs = afma.parse_holder_rows(_ROWS, fishery="Northern Prawn Fishery")
    assert len(recs) == 2
    r = recs[0]
    assert r["name"] == "Australia Sample Seafoods Pty Ltd"
    assert r["status"] == "Current" and r["permit_no"] == "1005612"
    assert r["fishery"] == "Northern Prawn Fishery" and r["jurisdiction"] == "AU"


def test_parse_holder_rows_handles_alternate_name_header():
    rows = [["Concession Holder", "SFR Number", "Status"],
            ["Sample Tuna Co Pty Ltd", "SFR-99", "Active"]]
    recs = afma.parse_holder_rows(rows, fishery="Southern Bluefin Tuna")
    assert recs[0]["name"] == "Sample Tuna Co Pty Ltd" and recs[0]["permit_no"] == "SFR-99"


def test_parse_holder_rows_no_header_returns_empty():
    assert afma.parse_holder_rows([["x", "y"], ["a", "b"]], fishery="F") == []


def test_records_to_entities_are_au_fishing_companies():
    ents = afma.records_to_entities(afma.parse_holder_rows(_ROWS, fishery="Northern Prawn Fishery"))
    assert all(e["entity_type"] == "company" and e["jurisdiction"] == "AU"
               and e["sector"] == "commercial_fishing" for e in ents)
    assert ents[0]["license_no"] == "1005612" and "Northern Prawn" in ents[0]["notes"]


# ---- collect with injected fetchers ---------------------------------------

def test_collect_pipes_page_and_files_through_injection():
    page = '<a href="/sites/default/files/2026-06/test_fishery_1_june_2026.xlsx">x</a>'
    xlsx = _xlsx(["Owner Name", "Status", "Sample Holder Pty Ltd", "Current"],
                 '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c></row>'
                 '<row r="2"><c r="A2" t="s"><v>2</v></c><c r="B2" t="s"><v>3</v></c></row>')
    recs = afma.collect(fetch_page=lambda u: page, fetch_file=lambda u: xlsx)
    assert len(recs) == 1 and recs[0]["name"] == "Sample Holder Pty Ltd"


def test_collect_isolates_a_bad_file():
    page = ('<a href="/sites/default/files/2026-06/good_fishery_1_june_2026.xlsx">x</a>'
            '<a href="/sites/default/files/2026-06/bad_fishery_1_june_2026.xlsx">y</a>')
    good = _xlsx(["Owner Name", "Status", "Sample Good Pty Ltd", "Current"],
                 '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c></row>'
                 '<row r="2"><c r="A2" t="s"><v>2</v></c><c r="B2" t="s"><v>3</v></c></row>')

    def fetch_file(u):
        if "bad_" in u:
            raise ValueError("corrupt xlsx")
        return good
    recs = afma.collect(fetch_page=lambda u: page, fetch_file=fetch_file)
    assert len(recs) == 1 and recs[0]["name"] == "Sample Good Pty Ltd"  # bad file skipped
