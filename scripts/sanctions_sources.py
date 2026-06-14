#!/usr/bin/env python3
"""Sanctions / debarment sources -> sanctioned_entity records (deterministic).

Two keyless authoritative adverse-entity feeds, the highest-value sweep endpoints:

  * OFAC SDN  -- US Treasury Specially Designated Nationals list. The classic
    CSV (treasury.gov/ofac/downloads/sdn.csv) is keyless and downloadable. Fixed
    schema, NO header: ent_num, SDN_Name, SDN_Type, Program, Title, ... ('-0-' is
    an empty field; SDN_Type '-0-' = an ENTITY/organisation, vs 'individual'/
    'vessel'/'aircraft'). We keep the entities.

  * World Bank debarred firms -- the "Listing of Ineligible Firms & Individuals".
    The page loads a keyless JSON from apigwext.worldbank.org (...FIRM/
    SANCTIONED_FIRM) -- but a DIRECT request 401s; it needs the page's browser
    context, so we render + capture the response (like the DMW connector). Fields:
    SUPP_NAME, SUPP_TYPE_CODE (F=firm), COUNTRY_NAME/LAND1, DEBAR_FROM/TO_DATE,
    DEBAR_REASON. We keep the firms.

Design: the parsers (parse_sdn_csv / parse_worldbank_firms) are pure functions
tested against the real on-the-wire formats; the fetchers (download / browser
render) are thin and injectable. Output maps to the entity-KB sanctioned_entity
shape. Propose-only.

Usage:
    python scripts/sanctions_sources.py --ofac     # -> reports/entity_kb/sanctions_ofac_sdn.jsonl
    python scripts/sanctions_sources.py --worldbank # -> sanctions_worldbank_debarred.jsonl
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import io
import json
import sys
import urllib.request
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "Mozilla/5.0 (compatible; duecare-screen/1.0; +defensive anti-trafficking)"

OFAC_SDN_CSV = "https://www.treasury.gov/ofac/downloads/sdn.csv"
WORLDBANK_DEBARRED_PAGE = "https://www.worldbank.org/en/projects-operations/procurement/debarred-firms"
WORLDBANK_FIRM_MARKER = "SANCTIONED_FIRM"

_EMPTY = {"-0-", ""}


def _sibling(name: str):
    spec = importlib.util.spec_from_file_location(
        f"dc_{name}_for_sanctions", str(_ROOT / "scripts" / f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


# ---- OFAC SDN (keyless CSV) ------------------------------------------------

def parse_sdn_csv(text: str) -> list[dict]:
    """Parse OFAC sdn.csv (no header, fixed schema) -> sanctioned ENTITY records.
    Individuals/vessels/aircraft are skipped; SDN_Type '-0-' = an entity."""
    recs = []
    for row in csv.reader(io.StringIO(text or "")):
        if len(row) < 4:
            continue
        name = (row[1] or "").strip()
        sdn_type = (row[2] or "").strip().lower()
        if not name or name in _EMPTY:
            continue
        if sdn_type in ("individual", "vessel", "aircraft"):
            continue  # keep entities/organisations only
        program = (row[3] or "").strip()
        remarks = (row[11] or "").strip() if len(row) > 11 else ""
        note = "OFAC SDN" + (f"; program {program}" if program not in _EMPTY else "")
        if remarks and remarks not in _EMPTY:
            note += f"; {remarks}"
        recs.append({"entity_type": "sanctioned_entity", "name": name, "jurisdiction": "",
                     "status": "watchlisted", "source": "US OFAC SDN list",
                     "source_tier": "official", "notes": note[:240]})
    return recs


def _http_get(url: str, *, timeout: float = 60.0) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/csv,*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(20_000_000).decode("utf-8", "replace")


def fetch_ofac_sdn(*, fetch=None) -> list[dict]:
    fetch = fetch or _http_get
    return parse_sdn_csv(fetch(OFAC_SDN_CSV))


# ---- World Bank debarred (browser-captured JSON) --------------------------

def _find_firm_list(data):
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return data
    if isinstance(data, dict):
        for v in data.values():
            r = _find_firm_list(v)
            if r:
                return r
    return None


def parse_worldbank_firms(data) -> list[dict]:
    """Parse the World Bank SANCTIONED_FIRM JSON -> debarred FIRM records."""
    firms = _find_firm_list(data) or []
    recs = []
    for f in firms:
        if not isinstance(f, dict):
            continue
        if str(f.get("SUPP_TYPE_CODE", "")).upper() != "F":  # firms only (skip individuals)
            continue
        name = str(f.get("SUPP_NAME") or "").strip()
        if not name:
            continue
        addr = ", ".join(str(x) for x in (f.get("SUPP_ADDR"), f.get("SUPP_CITY"),
                                          f.get("COUNTRY_NAME")) if x)
        frm, to = f.get("DEBAR_FROM_DATE"), f.get("DEBAR_TO_DATE")
        recs.append({"entity_type": "sanctioned_entity", "name": name,
                     "jurisdiction": str(f.get("LAND1") or "")[:8], "address": addr,
                     "status": "delisted",  # debarred = banned from contracts
                     "status_as_of": str(frm or "")[:10],
                     "source": "World Bank debarred firms", "source_tier": "official",
                     "notes": f"debarred {frm}->{to}: {f.get('DEBAR_REASON', '')}"[:240]})
    return recs


def fetch_worldbank_debarred() -> list[dict]:
    """Render the debarred-firms page and capture the keyless SANCTIONED_FIRM JSON
    (a direct request 401s -- it needs the page context)."""
    bs = _sibling("browser_scrape")
    from playwright.sync_api import sync_playwright
    captured = {}
    with sync_playwright() as pw:
        browser = bs._launch_browser(pw)
        page = browser.new_context(user_agent=bs.USER_AGENT).new_page()

        def on_resp(r):
            if WORLDBANK_FIRM_MARKER in r.url:
                try:
                    captured["body"] = r.text()
                except Exception:  # noqa: BLE001
                    pass
        page.on("response", on_resp)
        page.goto(WORLDBANK_DEBARRED_PAGE, wait_until="domcontentloaded", timeout=40000)
        try:
            page.wait_for_load_state("networkidle", timeout=20000)
        except Exception:  # noqa: BLE001
            pass
        browser.close()
    if "body" not in captured:
        return []
    try:
        return parse_worldbank_firms(json.loads(captured["body"]))
    except Exception:  # noqa: BLE001
        return []


# ---- CLI -------------------------------------------------------------------

def _write(records: list[dict], out: Path) -> None:
    ekb = _sibling("entity_kb")
    out.parent.mkdir(parents=True, exist_ok=True)
    ekb.save_entities(out, ekb.merge_entities([ekb.record_from_dict(r) for r in records]))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ofac", action="store_true", help="OFAC SDN entities")
    ap.add_argument("--worldbank", action="store_true", help="World Bank debarred firms")
    ap.add_argument("--out", default="")
    args = ap.parse_args(argv)

    if args.ofac:
        recs = fetch_ofac_sdn()
        out = Path(args.out) if args.out else (_ROOT / "reports" / "entity_kb" / "sanctions_ofac_sdn.jsonl")
        _write(recs, out)
        print(f"OFAC SDN: {len(recs)} sanctioned entities -> {out}", file=sys.stderr)
    elif args.worldbank:
        recs = fetch_worldbank_debarred()
        out = Path(args.out) if args.out else (_ROOT / "reports" / "entity_kb" / "sanctions_worldbank_debarred.jsonl")
        _write(recs, out)
        print(f"World Bank debarred: {len(recs)} firms -> {out}", file=sys.stderr)
    else:
        ap.error("provide --ofac or --worldbank")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
