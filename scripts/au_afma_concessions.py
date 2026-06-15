#!/usr/bin/env python3
"""Australia AFMA commercial-fishery concession-holder collector (deterministic XLSX).

The Australian Fisheries Management Authority publishes, per Commonwealth-managed
fishery, an Excel spreadsheet of current concession / statutory-fishing-right
(SFR) holders (Northern Prawn Fishery, Southern Bluefin Tuna, Eastern Tuna and
Billfish, and 15+ others). Commercial fishing is a tier-1 forced-labour sector,
so the roster of who holds a concession in each fishery is a direct screening
surface.

openpyxl is not available in this environment, so this module ships a tiny
stdlib XLSX reader (zipfile + ElementTree, resolving the shared-string table).
The per-fishery sheets share a stable shape -- a title row, a header row
(``Owner Name | Fishery | Operational Status | Permit Number | ...``), then data
rows -- so ``parse_holder_rows`` detects the header by synonym and maps the
holder-name / status / permit columns tolerantly across fisheries.

The page's download links are messy (some carry a doubled ``https://`` prefix or
a concatenated suffix, and each fishery appears for several months), so
``clean_xlsx_links`` normalises them and keeps the latest file per fishery.

Page fetch + file fetch are injectable; the row interpreter and link cleaner are
tested offline, and the XLSX reader is tested against an in-memory workbook.
Propose-only.

Usage:
    python scripts/au_afma_concessions.py                 # download + parse all fisheries
    python scripts/au_afma_concessions.py --max-files 3
"""
from __future__ import annotations

import argparse
import importlib.util
import io
import re
import sys
import urllib.request
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = ("Mozilla/5.0 (compatible; duecare-recruitment-screen/1.0; "
              "+defensive anti-trafficking review; respects robots.txt)")

AFMA_BASE = "https://www.afma.gov.au"
AFMA_PAGE = "https://www.afma.gov.au/commercial-fishers/resources/concession-holders-and-sfr-conditions"

_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

_NAME_HDR = ("owner name", "concession holder", "sfr holder", "holder", "operator",
             "company", "name")
_STATUS_HDR = ("operational status", "status")
_PERMIT_HDR = ("permit number", "sfr number", "licence number", "permit", "sfr")


def _sibling(name: str):
    spec = importlib.util.spec_from_file_location(
        f"dc_{name}_for_afma", str(_ROOT / "scripts" / f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


# ---- stdlib XLSX reader ----------------------------------------------------

def _col_idx(ref: str) -> int:
    """Excel cell ref ('C5') -> 0-based column index (2)."""
    letters = re.match(r"([A-Za-z]+)", ref or "")
    idx = 0
    for ch in (letters.group(1).upper() if letters else ""):
        idx = idx * 26 + (ord(ch) - 64)
    return idx - 1 if idx else 0


def read_xlsx(data: bytes) -> list[list[str]]:
    """Decode the first worksheet of an XLSX into rows of string cells (stdlib only)."""
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


# ---- link discovery --------------------------------------------------------

def _clean_url(u: str) -> str:
    """Fix AFMA's malformed hrefs: keep from the last https://, truncate after .xlsx."""
    i = u.rfind("https://")
    if i > 0:
        u = u[i:]
    m = re.search(r"\.xlsx?", u, re.I)
    if m:
        u = u[:m.end()]
    if u.startswith("/"):
        u = AFMA_BASE + u
    return u


def _fishery_key(url: str) -> str:
    """Group key for a fishery, ignoring the date/version/permits suffix."""
    base = re.sub(r"\.xlsx?$", "", url.rsplit("/", 1)[-1].lower())
    base = re.sub(r"_\d{1,2}_[a-z]+_\d{4}$", "", base)       # _2_june_2026
    base = re.sub(r"_(permits?|conditions?)$", "", base)
    return base


def _path_date(url: str) -> str:
    """The /YYYY-MM/ folder date used to pick the most recent file ('' if absent)."""
    m = re.search(r"/(\d{4})-(\d{2})/", url)
    return m.group(0) if m else ""


def clean_xlsx_links(html: str) -> list[str]:
    """Extract, normalise, and keep the LATEST xlsx file per fishery from the page."""
    raw = re.findall(r'href="([^"]+\.xlsx?[^"]*)"', html or "", re.I)
    latest: dict[str, str] = {}
    for u in (_clean_url(x) for x in raw):
        if not u.lower().endswith((".xlsx", ".xls")):
            continue
        key = _fishery_key(u)
        if key not in latest or _path_date(u) > _path_date(latest[key]):
            latest[key] = u
    return sorted(latest.values())


# ---- row interpretation ----------------------------------------------------

def _find_header(rows: list[list[str]]) -> int:
    """Index of the header row (the first row carrying a holder-name header)."""
    for i, row in enumerate(rows[:8]):
        low = [c.strip().lower() for c in row]
        if any(any(h == cell or h in cell for h in _NAME_HDR) for cell in low if cell):
            if sum(1 for c in row if c.strip()) >= 2:
                return i
    return -1


def _match_col(header: list[str], synonyms) -> int:
    low = [c.strip().lower() for c in header]
    for syn in synonyms:                      # exact first, then contains
        for i, cell in enumerate(low):
            if cell == syn:
                return i
    for syn in synonyms:
        for i, cell in enumerate(low):
            if syn in cell:
                return i
    return -1


def parse_holder_rows(rows: list[list[str]], *, fishery: str) -> list[dict]:
    """Extract concession-holder records from one fishery's decoded rows."""
    h = _find_header(rows)
    if h < 0:
        return []
    header = rows[h]
    name_c = _match_col(header, _NAME_HDR)
    status_c = _match_col(header, _STATUS_HDR)
    permit_c = _match_col(header, _PERMIT_HDR)
    if name_c < 0:
        return []
    recs: list[dict] = []
    for row in rows[h + 1:]:
        name = row[name_c].strip() if name_c < len(row) else ""
        if not name or name.lower() in ("owner name", "holder", "name"):
            continue
        recs.append({
            "name": name,
            "status": (row[status_c].strip() if 0 <= status_c < len(row) else ""),
            "permit_no": (row[permit_c].strip() if 0 <= permit_c < len(row) else ""),
            "fishery": fishery, "jurisdiction": "AU",
            "source": f"AFMA concession holders - {fishery}",
            "source_tier": "official",
        })
    return recs


def _fishery_label(url: str) -> str:
    return _fishery_key(url).replace("_", " ").title()


def collect(*, fetch_page=None, fetch_file=None, max_files: int | None = None) -> list[dict]:
    """Discover per-fishery files, download + parse each. Both fetchers injectable."""
    fetch_page = fetch_page or (lambda u: urllib.request.urlopen(
        urllib.request.Request(u, headers={"User-Agent": USER_AGENT}), timeout=60
    ).read(3_000_000).decode("utf-8", "ignore"))
    fetch_file = fetch_file or (lambda u: urllib.request.urlopen(
        urllib.request.Request(u, headers={"User-Agent": USER_AGENT}), timeout=90
    ).read(8_000_000))

    links = clean_xlsx_links(fetch_page(AFMA_PAGE))
    if max_files:
        links = links[:max_files]
    out: list[dict] = []
    for url in links:
        try:
            rows = read_xlsx(fetch_file(url))
            out.extend(parse_holder_rows(rows, fishery=_fishery_label(url)))
        except Exception:  # noqa: BLE001 -- one bad file never aborts the sweep
            continue
    return out


def records_to_entities(records: list[dict]) -> list[dict]:
    """Map AFMA concession-holder records to company entity dicts (AU)."""
    out = []
    for r in records:
        name = r.get("name", "")
        if not name:
            continue
        notes = f"AFMA concession holder - {r.get('fishery','')}".strip()
        if r.get("permit_no"):
            notes += f"; permit {r['permit_no']}"
        out.append({
            "entity_type": "company", "name": name, "jurisdiction": "AU",
            "status": r.get("status", "") or "current",
            "sector": "commercial_fishing",
            "license_no": r.get("permit_no", ""),
            "source": r.get("source", "AFMA concession holders"),
            "source_tier": r.get("source_tier", "official"),
            "notes": notes,
        })
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--max-files", type=int, default=None, help="limit how many fishery files")
    ap.add_argument("--out", default=str(_ROOT / "reports" / "entity_kb" / "au_afma_concessions.jsonl"))
    args = ap.parse_args(argv)

    try:
        records = collect(max_files=args.max_files)
    except Exception as exc:  # noqa: BLE001
        print(f"AFMA fetch/parse failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    entities = records_to_entities(records)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    ekb = _sibling("entity_kb")
    ekb.save_entities(out, ekb.merge_entities([ekb.record_from_dict(e) for e in entities]))
    from collections import Counter
    print(f"AU AFMA: {len(entities)} concession-holder rows -> {out}", file=sys.stderr)
    print(f"  fisheries: {len(set(r['fishery'] for r in records))}; "
          f"top holders: {dict(Counter(r['name'] for r in records).most_common(3))}", file=sys.stderr)
    return 0 if entities else 1


if __name__ == "__main__":
    raise SystemExit(main())
