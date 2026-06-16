#!/usr/bin/env python3
"""Reusable registry parsers -- one interface for HTML / CSV / XLSX / JSON / PDF.

The 9 hand-written deterministic resolvers (bd_oep, bd_mra, hk_money_lenders,
cn_mara, au_afma, ...) each re-implement the same five parse shapes. This library
factors them out behind ONE idea: a ``fields`` map of

    {canonical_field: source_locator}

where ``source_locator`` is a column header NAME, a 0-based column INDEX, a JSON
key, or (for PDF) a regex group number. Each parser returns a uniform list of
record dicts keyed by the canonical fields. That lets the long tail of
catalogued data-endpoints be onboarded as CONFIG (a per-source spec) instead of a
new Python module each -- see registry_spec.py.

Tabular formats (HTML table / CSV / XLSX) all reduce to rows-of-cells and share
``parse_table`` (header detection by field-name, or positional index mode, plus
an optional row_filter). JSON and PDF have their own key-based / regex-based
front-ends. Pure functions over in-memory content; fully tested offline.
"""
from __future__ import annotations

import csv as _csv
import html as _html
import io
import re
import zipfile
import xml.etree.ElementTree as ET
from typing import Any

_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

# ---------------------------------------------------------------------------
# XLSX reader (stdlib; canonical home for the reader au_afma also uses)
# ---------------------------------------------------------------------------

def _col_idx(ref: str) -> int:
    letters = re.match(r"([A-Za-z]+)", ref or "")
    idx = 0
    for ch in (letters.group(1).upper() if letters else ""):
        idx = idx * 26 + (ord(ch) - 64)
    return idx - 1 if idx else 0


def read_xlsx(data: bytes) -> list[list[str]]:
    """Decode the first worksheet of an XLSX into rows of string cells (stdlib)."""
    z = zipfile.ZipFile(io.BytesIO(data))
    shared: list[str] = []
    if "xl/sharedStrings.xml" in z.namelist():
        sst = ET.fromstring(z.read("xl/sharedStrings.xml"))
        for si in sst.findall(f"{_NS}si"):
            shared.append("".join(t.text or "" for t in si.iter(f"{_NS}t")))
    sheets = sorted(n for n in z.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml$", n))
    if not sheets:
        return []
    sheet = ET.fromstring(z.read(sheets[0]))
    rows: list[list[str]] = []
    for row in sheet.findall(f".//{_NS}row"):
        cells: dict[int, str] = {}
        maxc = -1
        for c in row.findall(f"{_NS}c"):
            idx = _col_idx(c.get("r", ""))
            v = c.find(f"{_NS}v")
            inline = c.find(f"{_NS}is")
            if c.get("t") == "s" and v is not None and (v.text or "").isdigit():
                k = int(v.text)
                val = shared[k] if k < len(shared) else ""
            elif inline is not None:
                val = "".join(t.text or "" for t in inline.iter(f"{_NS}t"))
            else:
                val = v.text if v is not None else ""
            cells[idx] = (val or "").strip()
            maxc = max(maxc, idx)
        rows.append([cells.get(i, "") for i in range(maxc + 1)])
    return rows


# ---------------------------------------------------------------------------
# Shared tabular core
# ---------------------------------------------------------------------------

def _cell(row: list[str], idx: int) -> str:
    return row[idx].strip() if 0 <= idx < len(row) else ""


def _index_mode(fields: dict) -> bool:
    return bool(fields) and all(isinstance(v, int) for v in fields.values())


def _resolve_cols(header: list[str], fields: dict) -> dict[str, int]:
    """Map each canonical field to a column index (header name match, or int)."""
    low = [c.strip().lower() for c in header]
    out: dict[str, int] = {}
    for fld, src in fields.items():
        if isinstance(src, int):
            out[fld] = src
            continue
        s = str(src).strip().lower()
        idx = next((i for i, c in enumerate(low) if c == s), -1)
        if idx < 0:
            idx = next((i for i, c in enumerate(low) if c and (s in c or c in s)), -1)
        out[fld] = idx
    return out


def _row_ok(rec: dict, row_filter: dict | None) -> bool:
    if not row_filter:
        return True
    val = str(rec.get(row_filter.get("field", ""), ""))
    pat = row_filter.get("pattern", "")
    return bool(re.search(pat, val)) if pat else bool(val)


def parse_table(rows: list[list[str]], fields: dict, *,
                row_filter: dict | None = None, name_field: str = "name") -> list[dict]:
    """Map rows-of-cells to canonical records.

    ``fields`` values may be column HEADER NAMES (header auto-detected) or 0-based
    INDEXES (positional mode -- no header needed; use ``row_filter`` to drop the
    header/chrome rows). A record is kept only if its ``name_field`` is non-empty
    and it passes ``row_filter``.
    """
    if not rows:
        return []
    if _index_mode(fields):
        col, data = dict(fields), rows
    else:
        srcs = [str(v).lower() for v in fields.values() if not isinstance(v, int)]
        need = max(1, (len(srcs) + 1) // 2)
        h = -1
        for i, r in enumerate(rows[:12]):
            low = [c.strip().lower() for c in r]
            if sum(1 for s in srcs if any(s == c or (s in c and c) for c in low)) >= need:
                h = i
                break
        if h < 0:
            return []
        col, data = _resolve_cols(rows[h], fields), rows[h + 1:]
    recs = []
    for r in data:
        rec = {f: _cell(r, i) for f, i in col.items() if i >= 0}
        if not rec.get(name_field, "").strip():
            continue
        if not _row_ok(rec, row_filter):
            continue
        recs.append(rec)
    return recs


# ---------------------------------------------------------------------------
# Format front-ends
# ---------------------------------------------------------------------------

_ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
_CELL_RE = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S)


def _detag(fragment: str) -> str:
    return _html.unescape(re.sub(r"<[^>]+>", "", fragment or "")).replace("\xa0", " ").strip()


def html_rows(html: str) -> list[list[str]]:
    """Extract <tr>/<td> cells from HTML into rows-of-cells."""
    return [[re.sub(r"\s+", " ", _detag(c)) for c in _CELL_RE.findall(tr)]
            for tr in _ROW_RE.findall(html or "")]


def parse_html_table(html: str, fields: dict, **kw) -> list[dict]:
    return parse_table(html_rows(html), fields, **kw)


def parse_csv(text: str, fields: dict, **kw) -> list[dict]:
    rows = [list(r) for r in _csv.reader(io.StringIO(text or ""))]
    return parse_table(rows, fields, **kw)


def parse_xlsx(data: bytes, fields: dict, **kw) -> list[dict]:
    return parse_table(read_xlsx(data), fields, **kw)


def _dig(obj: Any, path: str):
    """Walk a dotted key path into nested dicts (return None if absent)."""
    cur = obj
    for part in (path or "").split("."):
        if not part:
            continue
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def json_items(data: Any, list_path: str | None = None) -> list[dict]:
    """Find the list of records inside a JSON payload."""
    if list_path:
        node = _dig(data, list_path)
        if isinstance(node, list):
            return [x for x in node if isinstance(x, dict)]
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for key in ("data", "result", "results", "rows", "records", "items", "response"):
            if isinstance(data.get(key), list):
                return [x for x in data[key] if isinstance(x, dict)]
        for v in data.values():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                return [x for x in v if isinstance(x, dict)]
    return []


def parse_json(data: Any, fields: dict, *, list_path: str | None = None,
               row_filter: dict | None = None, name_field: str = "name") -> list[dict]:
    """Map a JSON list to canonical records (``fields`` values are keys/paths)."""
    out = []
    for it in json_items(data, list_path):
        rec = {}
        for fld, src in fields.items():
            v = _dig(it, str(src)) if "." in str(src) else it.get(src)
            rec[fld] = "" if v is None else str(v).strip()
        if not rec.get(name_field, "").strip():
            continue
        if not _row_ok(rec, row_filter):
            continue
        out.append(rec)
    return out


def parse_pdf_lines(text: str, row_regex: str, groups: dict[str, int]) -> list[dict]:
    """Map PDF text lines to records via a per-line regex + group->field map."""
    rx = re.compile(row_regex)
    out = []
    for line in (text or "").splitlines():
        m = rx.match(line.strip())
        if not m:
            continue
        out.append({fld: (m.group(g) or "").strip() for fld, g in groups.items()})
    return out
