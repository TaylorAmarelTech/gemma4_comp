#!/usr/bin/env python3
"""GLEIF Level-2 Relationship Records -> corporate parent/child edges (CC0).

GLEIF publishes not just legal entities (see ``gleif_lei.py``) but their **Level-2
relationships**: which entity is consolidated by which parent. This connector pulls
those RR records from the LEI Records API (``/lei-records/{lei}/direct-parent-
relationship`` and ``.../ultimate-parent-relationship``, CC0, no key) and emits them as
**ownership-graph edges** in the same shape the BODS connector uses --
``parent --parent_of--> child`` keyed on the LEI (the canonical cross-registry id), so
the corporate hierarchy joins straight onto the entities ``gleif_lei.py`` resolves.

"No parent" comes back as a reporting-exception / 404 -- handled as simply no edge.
Parameterised + propose-only: pull by ``--lei`` or by ``--country`` (the country's LEIs
via gleif_lei, then each one's parents); never the whole 650k-record dump.

Usage:
    python scripts/gleif_rr.py --lei 254900TF64ASRE9OIT26
    python scripts/gleif_rr.py --country AE --limit 200 --out reports/entity_kb/gleif_rr_ae.jsonl
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import urllib.request
from pathlib import Path

_BASE = "https://api.gleif.org/api/v1/lei-records"
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36"
_KINDS = ("direct", "ultimate")
_WEIGHT = {"direct": 0.95, "ultimate": 0.9}


# ---------------------------------------------------------------------------
# Mapping (pure)
# ---------------------------------------------------------------------------

def parse_rr_record(payload: dict) -> dict | None:
    """One RR API payload -> a ``parent_of`` edge dict (None if it carries no relationship).

    startNode = child LEI, endNode = parent LEI (``IS_(ULTIMATELY_)CONSOLIDATED_BY``).
    Emits ``parent (subject) --parent_of--> child (object)``.
    """
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        return None
    rel = (data.get("attributes") or {}).get("relationship") or {}
    child = (rel.get("startNode") or {}).get("id")
    parent = (rel.get("endNode") or {}).get("id")
    if not child or not parent:
        return None
    rtype = rel.get("type") or ""
    kind = "ultimate" if "ULTIMATELY" in rtype else "direct"
    start = ""
    for p in rel.get("periods") or []:
        if p.get("type") == "RELATIONSHIP_PERIOD" and p.get("startDate"):
            start = str(p["startDate"])[:10]
            break
    return {
        "subject_id": parent, "predicate": "parent_of", "object_id": child,
        "source": "GLEIF Level-2 RR (CC0)", "weight": _WEIGHT[kind],
        "qualifier": {"rel_type": kind, "gleif_type": rtype,
                      "status": rel.get("status", ""), "start_date": start},
    }


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------

def rr_url(lei: str, kind: str) -> str:
    """API URL for a LEI's direct/ultimate parent relationship record."""
    return f"{_BASE}/{lei}/{kind}-parent-relationship"


def _urllib_fetch(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": _UA,
                                               "Accept": "application/vnd.api+json"})
    with urllib.request.urlopen(req, timeout=40) as r:  # noqa: S310 - https standards API
        return json.loads(r.read().decode("utf-8", "replace"))


def fetch_parent_edges(leis, *, kinds=_KINDS, fetch=_urllib_fetch) -> list[dict]:
    """For each LEI, pull its direct/ultimate parent RRs -> deduped parent_of edges.

    A LEI with no parent (reporting-exception / 404) simply yields no edge. ``fetch(url)
    -> parsed-json`` is injectable for offline tests.
    """
    seen: set = set()
    out: list[dict] = []
    for lei in leis:
        for kind in kinds:
            try:
                payload = fetch(rr_url(lei, kind))
            except Exception:  # noqa: BLE001 - no-parent / exempt / transient -> skip this one
                continue
            edge = parse_rr_record(payload)
            if not edge:
                continue
            key = (edge["subject_id"], edge["object_id"], edge["qualifier"]["rel_type"])
            if key not in seen:
                seen.add(key)
                out.append(edge)
    return out


def _sibling(name: str):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parent / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lei", help="comma list of LEIs to fetch parents for")
    ap.add_argument("--country", help="ISO-2: pull this country's LEIs then their parents")
    ap.add_argument("--limit", type=int, default=200, help="max LEIs when using --country")
    ap.add_argument("--out", help="propose-only edges JSONL (under reports/)")
    args = ap.parse_args(argv)

    if args.lei:
        leis = [s.strip() for s in args.lei.split(",") if s.strip()]
    elif args.country:
        gl = _sibling("gleif_lei")
        leis = [e["lei"] for e in gl.fetch_lei_records(country=args.country, limit=args.limit) if e.get("lei")]
        print(f"pulled {len(leis)} {args.country} LEIs", file=sys.stderr)
    else:
        ap.error("give --lei or --country")

    edges = fetch_parent_edges(leis)
    print(f"GLEIF RR: {len(edges)} parent_of edges from {len(leis)} LEIs", file=sys.stderr)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in edges), encoding="utf-8")
        print(f"wrote {out} -- PROPOSE-ONLY")
    else:
        for e in edges[:12]:
            q = e["qualifier"]
            print(f"  {e['subject_id']} --parent_of[{q['rel_type']}]--> {e['object_id']}  ({q['status']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
