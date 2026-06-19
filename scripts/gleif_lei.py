#!/usr/bin/env python3
"""GLEIF LEI connector -- pull legal entities from the GLEIF LEI Records API (CC0).

The full GLEIF Golden Copy is a ~2.5M-row, multi-GB daily dump. Rather than pin that
on a fragile box, this connector uses the filterable, paginated **LEI Records API**
(``api.gleif.org/api/v1/lei-records`` -- JSON:API, CC0, no key) so we pull only the
slice we want: by country, by legal-name search, and/or by registration status, in
bounded pages. The Legal Entity Identifier is the canonical CC0 join-key across every
other registry we hold, so even a corridor-country slice is high value.

Propose-only: prints/writes records, never mutates the live KB. ``fetch`` is injectable
so the mapping + pagination are unit-tested offline against a real JSON:API fixture.

Usage:
    python scripts/gleif_lei.py --country AE --limit 500
    python scripts/gleif_lei.py --name "manpower" --limit 100 --out reports/entity_kb/gleif_ae.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

_BASE = "https://api.gleif.org/api/v1/lei-records"
_MAX_PAGE = 200  # GLEIF caps page[size] at 200
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36"


# ---------------------------------------------------------------------------
# Mapping (pure)
# ---------------------------------------------------------------------------

def _address(addr: dict) -> str:
    if not isinstance(addr, dict):
        return ""
    parts = list(addr.get("addressLines") or [])
    for k in ("city", "region", "postalCode", "country"):
        if addr.get(k):
            parts.append(str(addr[k]))
    return ", ".join(p for p in parts if p)


def parse_lei_record(rec: dict) -> dict | None:
    """One JSON:API LEI record -> a canonical entity dict (None if no legal name)."""
    attrs = rec.get("attributes") or {}
    ent = attrs.get("entity") or {}
    name = ((ent.get("legalName") or {}).get("name") or "").strip()
    if not name:
        return None
    addr = ent.get("legalAddress") or {}
    juris = (ent.get("jurisdiction") or addr.get("country") or "").strip()
    other = [n.get("name") for n in (ent.get("otherNames") or []) if isinstance(n, dict) and n.get("name")]
    return {
        "name": name,
        "lei": (attrs.get("lei") or "").strip(),
        "entity_type": "company",
        "jurisdiction": juris,
        "status": (attrs.get("registration") or {}).get("status", ""),
        "legal_form": (ent.get("legalForm") or {}).get("id", ""),
        "entity_status": ent.get("status", ""),
        "address": _address(addr),
        "aliases": other,
        "source": "GLEIF LEI (api.gleif.org, CC0)",
    }


# ---------------------------------------------------------------------------
# Fetch + paginate
# ---------------------------------------------------------------------------

def build_url(*, country: str | None = None, name: str | None = None,
              status: str | None = None, page: int = 1, page_size: int = _MAX_PAGE) -> str:
    """JSON:API query URL with the GLEIF bracketed page/filter params."""
    params = {"page[size]": min(page_size, _MAX_PAGE), "page[number]": page}
    if country:
        params["filter[entity.legalAddress.country]"] = country.upper()
    if name:
        params["filter[entity.legalName]"] = name
    if status:
        params["filter[registration.status]"] = status.upper()
    return _BASE + "?" + urllib.parse.urlencode(params)


def _urllib_fetch(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": _UA,
                                               "Accept": "application/vnd.api+json"})
    with urllib.request.urlopen(req, timeout=40) as r:  # noqa: S310 - https standards API
        return json.loads(r.read().decode("utf-8", "replace"))


def fetch_lei_records(*, country: str | None = None, name: str | None = None,
                      status: str | None = None, limit: int = 200, page_size: int = _MAX_PAGE,
                      fetch=_urllib_fetch) -> list[dict]:
    """Paginate the API and return up to ``limit`` mapped entities.

    Stops at ``limit`` or the API's ``meta.pagination.lastPage`` -- never an unbounded
    crawl. ``fetch(url) -> parsed-json`` is injectable for offline tests.
    """
    out: list[dict] = []
    page = 1
    while len(out) < limit:
        payload = fetch(build_url(country=country, name=name, status=status,
                                  page=page, page_size=min(page_size, limit)))
        for rec in payload.get("data") or []:
            mapped = parse_lei_record(rec)
            if mapped:
                out.append(mapped)
                if len(out) >= limit:
                    break
        last = ((payload.get("meta") or {}).get("pagination") or {}).get("lastPage", page)
        if page >= last or not payload.get("data"):
            break
        page += 1
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--country", help="ISO-2 country of legal address (e.g. AE, PH)")
    ap.add_argument("--name", help="legal-name search filter")
    ap.add_argument("--status", help="registration status (e.g. ISSUED, LAPSED)")
    ap.add_argument("--limit", type=int, default=200, help="max records (default 200)")
    ap.add_argument("--out", help="propose-only JSONL output path (under reports/)")
    args = ap.parse_args(argv)
    if not (args.country or args.name):
        ap.error("give at least --country or --name (the API is too large to pull whole)")

    ents = fetch_lei_records(country=args.country, name=args.name, status=args.status,
                             limit=args.limit)
    print(f"GLEIF: {len(ents)} entities "
          f"(country={args.country} name={args.name} status={args.status})", file=sys.stderr)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in ents), encoding="utf-8")
        print(f"wrote {out} -- PROPOSE-ONLY")
    else:
        for e in ents[:10]:
            print(f"  {e['lei']}  {e['name'][:48]}  [{e['jurisdiction']}] {e['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
