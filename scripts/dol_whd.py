#!/usr/bin/env python3
"""US DOL Wage & Hour Division enforcement connector -> employer-violation entities.

The WHD "Enforcement" dataset (DOL Open Data v4, dataset 10362, table WHD_enforcement)
holds **every concluded WHD compliance action since FY2005** -- the named employer, back
wages owed, employees due, civil penalties, industry (NAICS), and per-statute violation
counts. The migrant-labour signal is the point: H-2A (seasonal agricultural visa), H-2B,
H-1B, **MSPA** (Migrant & Seasonal Agricultural Worker Protection Act), SRAW, and child-
labour (FLSA-CL) violation counts -- an employer with those is a labour-exploitation risk
that ``entity_screen`` can match against the recruitment registries.

Field map authored against the dataset's own keyless metadata + sample record
(``apiprod.dol.gov/v4/datasets/10362`` -> dataset_metadatum/dataset_preview, e.g.
"Reliant Energy Retail Services, LLC"). The DATA endpoint needs a **free X-API-KEY**
(register at dataportal.dol.gov; set ``DOL_API_KEY``); ``parse_record`` is verified
against that real preview row offline. Propose-only.

Usage (after `set DOL_API_KEY=...`):
    python scripts/dol_whd.py --limit 500 --migrant-only
    python scripts/dol_whd.py --limit 2000 --out reports/entity_kb/dol_whd.jsonl
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

_DATA_URL = "https://api.dol.gov/v4/get/WHD/enforcement/json"
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36"
# per-statute programs with a migrant-labour / exploitation nexus (real column prefixes)
_MIGRANT_PROGRAMS = ("h2a", "h2b", "h1b", "h1a", "mspa", "sraw")


def _num(v) -> float:
    try:
        return float(v)
    except (ValueError, TypeError):
        return 0.0


def parse_record(rec: dict) -> dict:
    """One WHD_enforcement row -> a canonical employer-violation entity."""
    name = (rec.get("trade_nm") or rec.get("legal_name") or "").strip()
    addr = ", ".join(str(rec[k]) for k in ("street_addr_1_txt", "cty_nm", "st_cd", "zip_cd")
                     if rec.get(k))
    migrant = {p: int(_num(rec.get(f"{p}_violtn_cnt"))) for p in _MIGRANT_PROGRAMS}
    migrant = {p: c for p, c in migrant.items() if c > 0}
    case_viol = int(_num(rec.get("case_violtn_cnt")))
    return {
        "name": name, "legal_name": (rec.get("legal_name") or "").strip(),
        "entity_type": "employer", "jurisdiction": "US",
        "address": addr, "state": rec.get("st_cd", ""),
        "naics": rec.get("naic_cd", ""), "industry": rec.get("naics_code_description", ""),
        "case_id": rec.get("case_id", ""),
        "back_wages": _num(rec.get("bw_atp_amt")),
        "employees_due": int(_num(rec.get("ee_atp_cnt"))),
        "penalties": _num(rec.get("cmp_assd")),
        "violations": case_viol,
        "migrant_visa_violations": migrant,                   # h2a/h2b/h1b/mspa/sraw counts > 0
        "child_labor_violations": int(_num(rec.get("flsa_cl_violtn_cnt"))),
        "findings_start": str(rec.get("findings_start_date") or "")[:10],
        "findings_end": str(rec.get("findings_end_date") or "")[:10],
        "status": "violation" if case_viol > 0 else "no_violation",
        "source": "DOL WHD enforcement (api.dol.gov, US public domain)",
    }


def build_url(*, limit: int, offset: int) -> str:
    return _DATA_URL + "?" + urllib.parse.urlencode({"limit": limit, "offset": offset})


def _live_fetch(url: str, api_key: str) -> dict:
    sep = "&" if "?" in url else "?"
    req = urllib.request.Request(url + sep + urllib.parse.urlencode({"X-API-KEY": api_key}),
                                 headers={"User-Agent": _UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310 - https gov API
        return json.loads(r.read().decode("utf-8", "replace"))


def fetch_enforcement(*, api_key: str, max_records: int = 500, page_size: int = 500,
                      fetch=None) -> list[dict]:
    """Paginate the WHD enforcement endpoint -> parsed employer-violation entities."""
    do = fetch or (lambda url: _live_fetch(url, api_key))
    out: list[dict] = []
    offset = 0
    while len(out) < max_records:
        payload = do(build_url(limit=min(page_size, max_records), offset=offset))
        rows = payload.get("data") or []
        if not rows:
            break
        for rec in rows:
            out.append(parse_record(rec))
            if len(out) >= max_records:
                break
        offset += len(rows)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, default=500, help="max records (default 500)")
    ap.add_argument("--migrant-only", action="store_true",
                    help="keep only employers with H-2A/H-2B/H-1B/MSPA/SRAW violations")
    ap.add_argument("--api-key", help="DOL API key (else $DOL_API_KEY)")
    ap.add_argument("--out", help="propose-only JSONL (under reports/)")
    args = ap.parse_args(argv)

    key = args.api_key or os.environ.get("DOL_API_KEY")
    if not key:
        ap.error("DOL WHD data needs a free API key: register at https://dataportal.dol.gov "
                 "and set DOL_API_KEY (or pass --api-key). The schema/parser are verified; "
                 "only the live pull needs the key.")

    ents = fetch_enforcement(api_key=key, max_records=args.limit)
    if args.migrant_only:
        ents = [e for e in ents if e["migrant_visa_violations"]]
    n_mig = sum(1 for e in ents if e["migrant_visa_violations"])
    print(f"DOL WHD: {len(ents)} employers ({n_mig} with H-2A/B/MSPA-type violations)", file=sys.stderr)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in ents), encoding="utf-8")
        print(f"wrote {out} -- PROPOSE-ONLY")
    else:
        for e in ents[:12]:
            mig = e["migrant_visa_violations"]
            print(f"  {e['name'][:40]} [{e['state']}] bw=${e['back_wages']:.0f} "
                  f"viol={e['violations']}{' migrant='+str(mig) if mig else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
