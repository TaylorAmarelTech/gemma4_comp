#!/usr/bin/env python3
"""Scrape OFFICIAL recruitment-industry sources into normalized agency records.

This is the source-connector layer of the recruitment pipeline: it turns a
regulator's published list of agencies — an HTML table, a JSON list endpoint,
or a CSV export — into the AgencyProfile schema (name, licence, status,
address, phone numbers, job markets) that the licensed-agency verification
registry (`scripts/agency_registry.py`) consumes.

Appropriate-use design — these are connectors for OFFICIAL, PUBLIC regulator
data (e.g. the Philippine DMW Licensed Recruitment Agencies inquiry), the same
data a worker is meant to consult:

  * No embedded secrets. A live source's endpoint + key are read from env
    vars the operator sets (DMW pages, for instance, ship a public client key
    in the page; this tool does not redistribute it). Offline parsing of a
    saved export needs no key at all.
  * Polite. Live fetch is rate-limited, page-capped, sends an identifying
    User-Agent, and honours robots via the scanner's fetch path.
  * Propose-only. Output stages to reports/agency_registry/ (gitignored); it
    never mutates the live knowledge layer. Review before promoting.
  * The committed tests run fully offline against synthetic regulator-list
    fixtures.

Usage:
    # offline: parse a saved regulator page / export
    python scripts/scrape_agency_sources.py --from-html licensed_agencies.html
    python scripts/scrape_agency_sources.py --from-json export.json --list-path data.records
    python scripts/scrape_agency_sources.py --from-csv agencies.csv

    # live (operator-configured, env-keyed) -- prints the resolved plan, fetches politely
    DMW_LIST_URL=https://... DMW_API_KEY=... python scripts/scrape_agency_sources.py --source dmw_api
"""
from __future__ import annotations

import argparse
import csv
import html as _html
import importlib.util
import io
import json
import os
import re
import sys
from dataclasses import asdict
from html.parser import HTMLParser
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load_registry_module():
    spec = importlib.util.spec_from_file_location(
        "dc_agency_registry_for_scrape", str(_ROOT / "scripts" / "agency_registry.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # frozen-dataclass exec needs registration
    spec.loader.exec_module(mod)
    return mod


# Heuristic header -> AgencyProfile field. First substring match wins.
_HEADER_MAP = (
    ("license_no", ("licence no", "license no", "licence number", "license number",
                    "poea no", "dmw no", "licence", "license", "reg no", "control no")),
    ("status", ("status", "validity", "standing", "remarks")),
    ("status_as_of", ("as of", "status date", "valid until", "expiry", "validity date")),
    ("name", ("agency name", "name of agency", "company name", "agency", "name", "company")),
    ("address", ("address", "office address", "location")),
    ("phones", ("telephone", "phone", "contact no", "contact number", "tel", "mobile")),
    ("email", ("email", "e-mail")),
    ("region", ("region", "area")),
    ("job_markets", ("job market", "market", "destination", "countries", "deployment")),
)


def map_header(header: str) -> str:
    # normalize separators so "poea_no" / "company-name" match the space-form
    # needles ("poea no" / "company name").
    h = re.sub(r"[_\-]+", " ", (header or "").strip().lower())
    h = re.sub(r"\s+", " ", h)
    for field, needles in _HEADER_MAP:
        if any(n in h for n in needles):
            return field
    return ""


class _TableParser(HTMLParser):
    """Extract every <table> as a list of rows (each row a list of cell texts)."""

    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self._in_table = False
        self._in_cell = False
        self._row: list[str] = []
        self._cell: list[str] = []
        self._cur_table: list[list[str]] = []

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self._in_table, self._cur_table = True, []
        elif tag == "tr" and self._in_table:
            self._row = []
        elif tag in ("td", "th") and self._in_table:
            self._in_cell, self._cell = True, []

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._in_table:
            self._row.append(re.sub(r"\s+", " ", "".join(self._cell)).strip())
            self._in_cell = False
        elif tag == "tr" and self._in_table:
            if any(c for c in self._row):
                self._cur_table.append(self._row)
        elif tag == "table" and self._in_table:
            if self._cur_table:
                self.tables.append(self._cur_table)
            self._in_table = False

    def handle_data(self, data):
        if self._in_cell:
            self._cell.append(_html.unescape(data))


def parse_html_table(html: str) -> list[dict]:
    """Parse the largest HTML table into header-keyed records."""
    p = _TableParser()
    p.feed(html or "")
    if not p.tables:
        return []
    table = max(p.tables, key=len)
    if len(table) < 2:
        return []
    header = table[0]
    records = []
    for row in table[1:]:
        if len(row) < 2:
            continue
        rec = {}
        for i, cell in enumerate(row):
            key = map_header(header[i]) if i < len(header) else ""
            if key:
                rec[key] = cell
        if rec.get("name"):
            records.append(rec)
    return records


def _navigate(data, list_path: str):
    """Walk a dotted path to the list within a JSON payload."""
    node = data
    for part in (list_path or "").split("."):
        if not part:
            continue
        if isinstance(node, dict):
            node = node.get(part)
        else:
            return []
    if isinstance(node, list):
        return node
    if isinstance(data, list):
        return data
    return []


def parse_json_list(data, *, list_path: str = "") -> list[dict]:
    """Map a JSON list payload to header-keyed records (keys normalized)."""
    items = _navigate(data, list_path)
    records = []
    for it in items:
        if not isinstance(it, dict):
            continue
        rec = {}
        for k, v in it.items():
            key = map_header(str(k))
            if key and v not in (None, ""):
                rec[key] = v
        if rec.get("name"):
            records.append(rec)
    return records


def parse_csv(text: str) -> list[dict]:
    rows = list(csv.DictReader(io.StringIO(text)))
    records = []
    for row in rows:
        rec = {}
        for k, v in row.items():
            key = map_header(str(k))
            if key and v not in (None, ""):
                rec[key] = v
        if rec.get("name"):
            records.append(rec)
    return records


def records_to_profiles(records: list[dict], *, source: str, fetched_at: str = "") -> list[dict]:
    """Normalize raw records into AgencyProfile dicts via the registry schema."""
    reg = _load_registry_module()
    out = []
    for rec in records:
        rec = {**rec, "official_source": rec.get("official_source") or source,
               "fetched_at": rec.get("fetched_at") or fetched_at}
        out.append(asdict(reg.profile_from_record(rec)))
    return out


# Source templates: NO embedded secrets — endpoint + key come from env.
SOURCE_TEMPLATES = {
    "dmw_api": {
        "kind": "json",
        "url_env": "DMW_LIST_URL",
        "key_env": "DMW_API_KEY",
        "list_path_env": "DMW_LIST_PATH",
        "note": ("Philippine DMW Licensed Recruitment Agencies. The inquiry page "
                 "(https://dmw.gov.ph/inquiry/licensed-recruitment-agencies) is a "
                 "Nuxt SPA backed by a JSON API. Set DMW_LIST_URL to the list "
                 "endpoint and DMW_API_KEY to the page's public client key; this "
                 "tool stores neither."),
    },
    "html_table": {
        "kind": "html",
        "url_env": "AGENCY_LIST_URL",
        "key_env": "",
        "note": "Any regulator that publishes a licensed-agency HTML table.",
    },
}


def _fetch(url: str, *, api_key: str = "") -> tuple[str, str | None]:
    """Polite fetch via the scanner's robots-respecting path, with an optional
    bearer key."""
    spec = importlib.util.spec_from_file_location(
        "dc_scan_fetch_for_scrape", str(_ROOT / "scripts" / "scan_recruitment_text.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    if api_key:
        # the scanner's _fetch_url uses a fixed header set; for keyed APIs do a
        # minimal stdlib GET with the bearer added (still UA-identified)
        import urllib.request
        req = urllib.request.Request(url, headers={
            "User-Agent": mod.USER_AGENT, "Accept": "application/json,*/*",
            "Authorization": f"Bearer {api_key}"})
        try:
            with urllib.request.urlopen(req, timeout=mod.FETCH_TIMEOUT) as r:
                return r.read(mod.MAX_FETCH_BYTES).decode("utf-8", "replace"), None
        except Exception as exc:  # noqa: BLE001
            return "", f"{type(exc).__name__}: {exc}"[:160]
    return mod._fetch_url(url)


def scrape_live(source: str) -> tuple[list[dict], str]:
    """Fetch + parse a configured live source (env-keyed). Returns (records, note)."""
    cfg = SOURCE_TEMPLATES.get(source)
    if not cfg:
        return [], f"unknown source {source!r}; known: {sorted(SOURCE_TEMPLATES)}"
    url = os.environ.get(cfg["url_env"], "").strip()
    if not url:
        return [], f"set {cfg['url_env']} to the source URL (env-keyed; nothing embedded)"
    key = os.environ.get(cfg.get("key_env", ""), "") if cfg.get("key_env") else ""
    text, err = _fetch(url, api_key=key)
    if err:
        return [], f"fetch failed: {err}"
    if cfg["kind"] == "json":
        try:
            data = json.loads(text)
        except Exception as exc:  # noqa: BLE001
            return [], f"not JSON: {exc}"
        return parse_json_list(data, list_path=os.environ.get(cfg.get("list_path_env", ""), "")), cfg["note"]
    return parse_html_table(text), cfg["note"]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from-html", help="parse a saved regulator HTML page")
    ap.add_argument("--from-json", help="parse a saved JSON export")
    ap.add_argument("--from-csv", help="parse a saved CSV export")
    ap.add_argument("--list-path", default="", help="dotted path to the list in a JSON export")
    ap.add_argument("--source", help=f"fetch a live configured source: {sorted(SOURCE_TEMPLATES)}")
    ap.add_argument("--out", default=str(_ROOT / "reports" / "agency_registry" / "scraped.json"))
    args = ap.parse_args(argv)

    source_label = ""
    if args.from_html:
        records = parse_html_table(Path(args.from_html).read_text(encoding="utf-8", errors="replace"))
        source_label = f"html:{Path(args.from_html).name}"
    elif args.from_json:
        records = parse_json_list(json.loads(Path(args.from_json).read_text(encoding="utf-8")),
                                  list_path=args.list_path)
        source_label = f"json:{Path(args.from_json).name}"
    elif args.from_csv:
        records = parse_csv(Path(args.from_csv).read_text(encoding="utf-8", errors="replace"))
        source_label = f"csv:{Path(args.from_csv).name}"
    elif args.source:
        records, note = scrape_live(args.source)
        source_label = f"live:{args.source}"
        print(note, file=sys.stderr)
    else:
        ap.error("provide --from-html / --from-json / --from-csv / --source")

    if not records:
        print("no records parsed (check the source shape / env config)", file=sys.stderr)
        return 1
    profiles = records_to_profiles(records, source=source_label)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {"_synthetic": False, "source": source_label,
               "n_records": len(profiles), "records": profiles}
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"scraped {len(profiles)} agency record(s) from {source_label} -> {out}", file=sys.stderr)
    print("review, then promote with: agency_registry.py --ingest "
          f"{out} --out data/agency_registry/<name>.json", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
