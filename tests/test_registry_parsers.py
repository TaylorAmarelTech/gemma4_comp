"""Tests for scripts/registry_parsers.py -- the unified format parsers.

Pure, offline: each parser maps in-memory content to canonical record dicts via a
fields map (header-name or index), with row filtering. The XLSX reader runs
against an in-memory workbook.
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


rp = _load("registry_parsers", _ROOT / "scripts" / "registry_parsers.py")

_NS = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'


def _xlsx(shared, rows_xml):
    sst = f"<sst {_NS}>" + "".join(f"<si><t>{s}</t></si>" for s in shared) + "</sst>"
    sheet = f"<worksheet {_NS}><sheetData>{rows_xml}</sheetData></worksheet>"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("xl/sharedStrings.xml", sst)
        z.writestr("xl/worksheets/sheet1.xml", sheet)
    return buf.getvalue()


# ---- parse_table (header mode) --------------------------------------------

def test_parse_table_header_mode_maps_by_name():
    rows = [["License No", "Agent Name", "Status"],
            ["RL01", "Alpha Agency", "Active"],
            ["RL02", "Beta Agency", "Cancelled"]]
    recs = rp.parse_table(rows, {"name": "Agent Name", "license_no": "License No",
                                 "status": "Status"})
    assert len(recs) == 2
    assert recs[0] == {"name": "Alpha Agency", "license_no": "RL01", "status": "Active"}


def test_parse_table_row_filter_drops_non_matching():
    rows = [["License No", "Agent Name"], ["RL01", "Alpha"], ["XX99", "NotAnAgent"]]
    recs = rp.parse_table(rows, {"name": "Agent Name", "license_no": "License No"},
                          row_filter={"field": "license_no", "pattern": "^RL"})
    assert [r["name"] for r in recs] == ["Alpha"]


def test_parse_table_index_mode_with_filter_skips_header():
    rows = [["Serial", "Name", "Score"], ["1", "Enterprise A", "117"], ["2", "Enterprise B", "89"]]
    recs = rp.parse_table(rows, {"rank": 0, "name": 1, "score": 2},
                          row_filter={"field": "rank", "pattern": r"^\d+$"})
    assert len(recs) == 2 and recs[0]["score"] == "117"  # header 'Serial' filtered out


def test_parse_table_skips_blank_name():
    rows = [["Name", "X"], ["", "y"], ["Real", "z"]]
    assert [r["name"] for r in rp.parse_table(rows, {"name": "Name", "x": "X"})] == ["Real"]


def test_parse_table_ignores_descriptive_title_row():
    # a title row whose prose merely CONTAINS a field word (Employer/Stream/...) must
    # not be picked as the header -- exact cell matches win (the real header is row 2)
    rows = [["Employers issued a positive LMIA by Stream and Occupation"],
            [""],
            ["Province/Territory", "Stream", "Employer", "Address", "Occupation"],
            ["Newfoundland", "High Wage", "Sample Health Authority", "St Johns", "Nurse"]]
    recs = rp.parse_table(rows, {"name": "Employer", "stream": "Stream", "address": "Address",
                                 "province": "Province/Territory", "occupation": "Occupation"})
    assert len(recs) == 1 and recs[0]["name"] == "Sample Health Authority"


# ---- html / csv / xlsx ----------------------------------------------------

def test_parse_html_table():
    html = ("<table><tr><th>Name</th><th>Status</th></tr>"
            "<tr><td>Acme &amp; Co</td><td>Active</td></tr></table>")
    recs = rp.parse_html_table(html, {"name": "Name", "status": "Status"})
    assert recs == [{"name": "Acme & Co", "status": "Active"}]


def test_parse_csv():
    text = "Name,License No\nAlpha,RL01\nBeta,RL02\n"
    recs = rp.parse_csv(text, {"name": "Name", "license_no": "License No"})
    assert len(recs) == 2 and recs[1]["license_no"] == "RL02"


def test_parse_xlsx_via_reader():
    data = _xlsx(["Name", "Status", "Sample Co", "Active"],
                 '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c></row>'
                 '<row r="2"><c r="A2" t="s"><v>2</v></c><c r="B2" t="s"><v>3</v></c></row>')
    recs = rp.parse_xlsx(data, {"name": "Name", "status": "Status"})
    assert recs == [{"name": "Sample Co", "status": "Active"}]


# ---- json -----------------------------------------------------------------

def test_parse_json_list_and_dotted_keys():
    data = [{"org": {"full": "Alpha Ltd"}, "lic": "001"}, {"org": {"full": "Beta"}, "lic": "002"}]
    recs = rp.parse_json(data, {"name": "org.full", "license_no": "lic"})
    assert recs[0] == {"name": "Alpha Ltd", "license_no": "001"}


def test_parse_json_unwraps_wrapper_and_list_path():
    assert rp.json_items({"data": [{"a": 1}]}) == [{"a": 1}]
    assert rp.json_items({"resp": {"items": [{"a": 1}]}}, list_path="resp.items") == [{"a": 1}]


def test_parse_json_skips_nameless():
    data = [{"n": "Has Name"}, {"n": ""}]
    assert len(rp.parse_json(data, {"name": "n"})) == 1


# ---- pdf ------------------------------------------------------------------

def test_parse_pdf_lines_by_regex_groups():
    text = "6323 56/2026 Sample Credit Ltd 8-Nov-26\nheader line ignored\n5762 1340/2025 Other Co 8-Sep-26"
    recs = rp.parse_pdf_lines(text, r"^(\d{3,5})\s+(\d+/\d{4})\s+(.+?)\s+(\d{1,2}-\w{3}-\d{2})$",
                              {"file_no": 1, "license_no": 2, "name": 3, "expiry": 4})
    assert len(recs) == 2
    assert recs[0]["name"] == "Sample Credit Ltd" and recs[0]["license_no"] == "56/2026"
