#!/usr/bin/env python3
"""Bangladesh OEP licensed overseas recruiting-agency collector (deterministic HTML).

The Bureau of Manpower, Employment and Training publishes the authoritative
register of licensed overseas recruiting agencies (manpower-export agents) at
https://www.oep.gov.bd/agencies. Bangladesh is one of the top labour-origin
countries, and these agencies are the tier-1 gatekeepers of every BD corridor --
the BD equivalent of the Philippine DMW list.

The page is a DataTables grid, but every row is server-rendered into the HTML
(DataTables only paginates client-side), so the full roster parses
DETERMINISTICALLY with no browser, no API, no tokens. Columns:

    # | License No (RLxxxx) | Agent Name | Address | Office Phone | License Status | Validity

Status is the watchlist signal: Active / Expired / Suspended / Cancelled /
Server Locked. The office phone is the agency's published business line (public
registry data, not individual PII).

Design mirrors hk_money_lenders: the download is injectable, so the parser and
the entity mapping are tested offline against the real row structure with no
network. Propose-only.

Usage:
    python scripts/bd_oep_agencies.py            # download + parse the live list
    python scripts/bd_oep_agencies.py --html path.html
"""
from __future__ import annotations

import argparse
import html as _html
import importlib.util
import re
import sys
import urllib.request
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = ("Mozilla/5.0 (compatible; duecare-recruitment-screen/1.0; "
              "+defensive anti-trafficking review; respects robots.txt)")

OEP_URL = "https://www.oep.gov.bd/agencies"

_ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
_CELL = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S)
_LICENSE = re.compile(r"^RL\s?\d", re.I)


def _sibling(name: str):
    spec = importlib.util.spec_from_file_location(
        f"dc_{name}_for_bdoep", str(_ROOT / "scripts" / f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _text(fragment: str) -> str:
    """Strip tags + collapse whitespace + unescape entities from a cell."""
    return _html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", fragment or ""))).strip()


def parse_oep_html(page: str) -> list[dict]:
    """Parse the OEP agencies page HTML into recruiting-agency records.

    A data row is any ``<tr>`` whose second cell is a licence number (``RLxxxx``);
    the header row and any chrome rows lack that pattern and are skipped, so the
    parse is robust to surrounding markup.
    """
    recs: list[dict] = []
    for tr in _ROW.findall(page or ""):
        cells = [_text(c) for c in _CELL.findall(tr)]
        if len(cells) >= 7 and _LICENSE.match(cells[1]):
            recs.append({
                "license_no": cells[1], "name": cells[2], "address": cells[3],
                "phone": cells[4], "status": cells[5] or "Unknown",
                "license_validity": cells[6], "jurisdiction": "BD",
                "source": "BD OEP/BMET licensed recruiting-agency register",
                "source_tier": "official",
            })
    return recs


def download_html(url: str = OEP_URL, *, fetch=None) -> str:
    """Download the agencies page (``fetch(url)->str`` injectable for tests)."""
    if fetch is not None:
        return fetch(url)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=90) as r:  # noqa: S310 (https gov URL)
        return r.read(12_000_000).decode("utf-8", "ignore")


def collect(*, fetch=None, html_path: str | None = None) -> list[dict]:
    """Download (or read) the agencies page and return agency records."""
    page = Path(html_path).read_text(encoding="utf-8", errors="ignore") if html_path \
        else download_html(fetch=fetch)
    return parse_oep_html(page)


def records_to_entities(records: list[dict]) -> list[dict]:
    """Map OEP agency records to recruitment_agency entity dicts (BD)."""
    out = []
    for r in records:
        name = r.get("name", "")
        if not name:
            continue
        notes = f"License No. {r.get('license_no','')}".strip()
        if r.get("license_validity"):
            notes += f"; valid to {r['license_validity']}"
        out.append({
            "entity_type": "recruitment_agency", "name": name, "jurisdiction": "BD",
            "status": r.get("status", "Unknown"),
            "address": r.get("address", ""), "phones": r.get("phone", ""),
            "license_no": r.get("license_no", ""),
            "source": r.get("source", "BD OEP recruiting-agency register"),
            "source_tier": r.get("source_tier", "official"),
            "notes": notes,
        })
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--html", help="parse a local copy of the agencies page")
    ap.add_argument("--out", default=str(_ROOT / "reports" / "entity_kb" / "bd_oep_agencies.jsonl"))
    args = ap.parse_args(argv)

    try:
        records = collect(html_path=args.html)
    except Exception as exc:  # noqa: BLE001
        print(f"OEP fetch/parse failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    entities = records_to_entities(records)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    ekb = _sibling("entity_kb")
    ekb.save_entities(out, ekb.merge_entities([ekb.record_from_dict(e) for e in entities]))
    from collections import Counter
    by_status = dict(Counter(r["status"] for r in records))
    print(f"BD OEP: {len(entities)} recruiting agencies -> {out}", file=sys.stderr)
    print(f"  by status: {by_status}", file=sys.stderr)
    return 0 if entities else 1


if __name__ == "__main__":
    raise SystemExit(main())
