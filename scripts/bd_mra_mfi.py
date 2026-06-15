#!/usr/bin/env python3
"""Bangladesh MRA licensed microfinance-institution collector (deterministic JSON).

The Microcredit Regulatory Authority runs a public e-verify register of licensed
microfinance institutions (MFIs) -- the statutory licensed money-lenders of
Bangladesh under the MRA Act 2006. The /mfilist.html page is a DataTables grid
fed by a clean JSON API, so the full roster parses DETERMINISTICALLY (no browser,
no tokens) straight off the endpoint:

    https://ndb.mra.gov.bd/mra_web/everify/mfi-list  ->  JSON list, fields:
      license_no, short_name_of_org, full_name_of_org,
      full_name_of_org_in_bengali, address_of_org, license_issue_date,
      licensing_year, email_address, licensing_state_id

Money lenders are a load-bearing trafficking vector (recruitment-fee debt
launders through licensed lenders), so a current roster of who is MRA-licensed
is a direct screening signal. ``licensing_state_id`` has two codes (30 / 130);
the e-verify page splits these into active/inactive counts but the public feed
does not document the mapping, so this collector records every institution as
``licensed`` (factual -- all are on the register) and RETAINS the raw state code
in notes rather than assert an active/cancelled label it cannot verify.

The org email is the institution's published business contact (public registry
data, not individual PII). The download is injectable; tested offline against the
real JSON shape. Propose-only.

Usage:
    python scripts/bd_mra_mfi.py            # download + parse the live list
    python scripts/bd_mra_mfi.py --json path.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import urllib.request
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = ("Mozilla/5.0 (compatible; duecare-recruitment-screen/1.0; "
              "+defensive anti-trafficking review; respects robots.txt)")

MRA_URL = "https://ndb.mra.gov.bd/mra_web/everify/mfi-list"


def _sibling(name: str):
    spec = importlib.util.spec_from_file_location(
        f"dc_{name}_for_bdmra", str(_ROOT / "scripts" / f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _items(data) -> list[dict]:
    """Pull the institution list out of the JSON (list, or a wrapper dict)."""
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for key in ("data", "result", "results", "rows"):
            if isinstance(data.get(key), list):
                return [x for x in data[key] if isinstance(x, dict)]
        for v in data.values():
            if isinstance(v, list):
                return [x for x in v if isinstance(x, dict)]
    return []


def parse_mfi_json(data) -> list[dict]:
    """Parse the MRA mfi-list JSON into licensed-MFI records."""
    recs: list[dict] = []
    for it in _items(data):
        name = str(it.get("full_name_of_org") or it.get("short_name_of_org") or "").strip()
        if not name:
            continue
        recs.append({
            "name": name,
            "name_local": str(it.get("full_name_of_org_in_bengali") or "").strip(),
            "short_name": str(it.get("short_name_of_org") or "").strip(),
            "license_no": str(it.get("license_no") or "").strip(),
            "address": str(it.get("address_of_org") or "").strip(),
            "license_issue_date": str(it.get("license_issue_date") or "").strip(),
            "email": str(it.get("email_address") or "").strip(),
            "state_id": str(it.get("licensing_state_id") or "").strip(),
            "status": "licensed",
            "jurisdiction": "BD",
            "source": "BD MRA licensed microfinance institutions (e-verify)",
            "source_tier": "official",
        })
    return recs


def download_json(url: str = MRA_URL, *, fetch=None):
    """Download + parse the JSON (``fetch(url)->str|bytes`` injectable for tests)."""
    if fetch is not None:
        raw = fetch(url)
        return json.loads(raw) if isinstance(raw, (str, bytes)) else raw
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:  # noqa: S310 (https gov URL)
        return json.loads(r.read(12_000_000).decode("utf-8", "ignore"))


def collect(*, fetch=None, json_path: str | None = None) -> list[dict]:
    """Download (or read) the JSON and return MFI records."""
    if json_path:
        return parse_mfi_json(json.loads(Path(json_path).read_text(encoding="utf-8")))
    return parse_mfi_json(download_json(fetch=fetch))


def records_to_entities(records: list[dict]) -> list[dict]:
    """Map MFI records to ``lender`` entity dicts (BD)."""
    out = []
    for r in records:
        name = r.get("name", "")
        if not name:
            continue
        notes = f"MRA Licence No. {r.get('license_no','')}".strip()
        if r.get("license_issue_date"):
            notes += f"; issued {r['license_issue_date']}"
        if r.get("state_id"):
            notes += f"; MRA state {r['state_id']}"
        if r.get("name_local"):
            notes += f"; {r['name_local']}"
        out.append({
            "entity_type": "lender", "name": name, "jurisdiction": "BD",
            "status": r.get("status", "licensed"),
            "address": r.get("address", ""),
            "license_no": r.get("license_no", ""),
            "source": r.get("source", "BD MRA licensed MFIs"),
            "source_tier": r.get("source_tier", "official"),
            "notes": notes,
        })
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", help="parse a local copy of the mfi-list JSON")
    ap.add_argument("--out", default=str(_ROOT / "reports" / "entity_kb" / "bd_mra_mfi.jsonl"))
    args = ap.parse_args(argv)

    try:
        records = collect(json_path=args.json)
    except Exception as exc:  # noqa: BLE001
        print(f"MRA fetch/parse failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    entities = records_to_entities(records)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    ekb = _sibling("entity_kb")
    ekb.save_entities(out, ekb.merge_entities([ekb.record_from_dict(e) for e in entities]))
    from collections import Counter
    print(f"BD MRA: {len(entities)} licensed MFIs -> {out}", file=sys.stderr)
    print(f"  by state code: {dict(Counter(r['state_id'] for r in records))}", file=sys.stderr)
    return 0 if entities else 1


if __name__ == "__main__":
    raise SystemExit(main())
