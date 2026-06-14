#!/usr/bin/env python3
"""Merge researched migrant-worker SUPPORT organisations into a catalogue.

The protective counterpart to ``merge_entity_sources.py``. Where that tool
catalogues registries of *licensed entities* (potential bad actors / subjects
to screen), this one catalogues the organisations that HELP migrant workers --
national helplines, shelters, legal-aid clinics, migrant unions, resource
centres, faith-based welfare missions, anti-trafficking NGOs, government labour
attaches, intergovernmental bodies, and seafarer-welfare networks. These are the
resources DueCare surfaces TO a worker (or NGO caseworker) when exploitation is
detected.

Takes a JSON payload of researched orgs (``{"orgs": [...]}`` or a bare list) and
folds it into ``configs/duecare/research_monitor/migrant_support_orgs.yaml``
deterministically and idempotently: org_type validated against a controlled
vocabulary, country upper-cased (or INTL), deterministic id, dedup by URL and by
(org_type, name, country), and ASCII text hygiene. Public org contact details
(hotline / office phone, general email) are kept; they are exactly the data a
worker needs. DRY-RUN by default; ``--apply`` writes.

Examples
--------
    python scripts/merge_support_orgs.py --incoming reports/_scratch/orgs.json --report
    python scripts/merge_support_orgs.py --incoming reports/_scratch/orgs.json --apply
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

_ROOT = Path(__file__).resolve().parents[1]
_CATALOG = _ROOT / "configs" / "duecare" / "research_monitor" / "migrant_support_orgs.yaml"


def _sibling(name: str):
    spec = importlib.util.spec_from_file_location(
        f"dc_{name}_for_orgs", str(_ROOT / "scripts" / f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


# reuse the text hygiene + url normalisation from the entity-source merge (DRY)
_mes = _sibling("merge_entity_sources")
sanitize_text = _mes.sanitize_text
_slug = _mes._slug
_norm_url = _mes._norm_url

#: organisation roles in the migrant-support ecosystem
ORG_TYPES: tuple[str, ...] = (
    "helpline", "shelter", "legal_aid", "migrant_union", "resource_center",
    "faith_based", "anti_trafficking_ngo", "govt_labour_attache", "intl_org",
    "seafarer_welfare", "repatriation", "research_advocacy", "other",
)
SCOPES: tuple[str, ...] = ("local", "national", "regional", "international")

_FIELDS = ("id", "name", "org_type", "country", "url", "contact_phone", "contact_email",
           "services", "languages", "scope", "url_verified", "notes", "confidence")


def make_id(country: str, org_type: str, name: str) -> str:
    """Deterministic id ``<cc>_<org_type[:12]>_<name-slug[:30]>``."""
    cc = re.sub(r"[^a-z0-9]", "", (country or "xx").lower())[:4] or "xx"
    ot = re.sub(r"[^a-z0-9_]", "", (org_type or "other").lower())[:12].strip("_")
    return f"{cc}_{ot}_{_slug(name, 30)}"


def normalize_org(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Coerce a researched org dict into a canonical catalogue row.

    Returns None when there is no name, or no way to reach the org at all
    (neither a URL nor a phone nor an email) -- a support entry with no contact
    is useless.
    """
    name = sanitize_text(str(raw.get("name") or "")).strip()
    if not name:
        return None
    url = str(raw.get("url") or "").strip()
    phone = sanitize_text(str(raw.get("contact_phone") or "")).strip()
    email = sanitize_text(str(raw.get("contact_email") or "")).strip()
    if not (url.lower().startswith("http") or phone or email):
        return None

    org_type = str(raw.get("org_type") or "other").strip().lower()
    if org_type not in ORG_TYPES:
        org_type = "other"
    country = re.sub(r"[^A-Za-z]", "", str(raw.get("country") or "")).upper()[:4] or "XX"
    if country != "INTL" and len(country) > 2:
        country = country[:2]
    scope = str(raw.get("scope") or "national").strip().lower()
    if scope not in SCOPES:
        scope = "national"
    try:
        confidence = max(0.0, min(1.0, float(raw.get("confidence", 0.6))))
    except (TypeError, ValueError):
        confidence = 0.6

    rec = {
        "id": str(raw.get("id") or "").strip() or make_id(country, org_type, name),
        "name": name,
        "org_type": org_type,
        "country": country,
        "url": url,
        "contact_phone": phone[:80],
        "contact_email": email[:120],
        "services": sanitize_text(str(raw.get("services") or "")).strip()[:500],
        "languages": sanitize_text(str(raw.get("languages") or "")).strip()[:120],
        "scope": scope,
        "url_verified": bool(raw.get("url_verified", False)),
        "notes": sanitize_text(str(raw.get("notes") or "")).strip()[:500],
        "confidence": round(confidence, 2),
    }
    return {k: rec[k] for k in _FIELDS}


def _coerce(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        for key in ("orgs", "organizations", "organisations", "results", "records"):
            if isinstance(payload.get(key), list):
                return [x for x in payload[key] if isinstance(x, dict)]
        return []
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    return []


def _dedup_key(rec: dict) -> tuple:
    """An org is a duplicate when same (org_type, normalized-name, country)."""
    return (rec["org_type"], _slug(rec["name"], 40), rec["country"])


def merge(existing: Iterable[dict[str, Any]],
          incoming: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Fold ``incoming`` orgs into ``existing``, deduped (URL or name-key) + sorted."""
    merged: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    seen_keys: set[tuple] = set()

    for raw in existing:
        rec = normalize_org(raw)
        if rec is None:
            continue
        merged.append(rec)
        if rec["url"]:
            seen_urls.add(_norm_url(rec["url"]))
        seen_keys.add(_dedup_key(rec))

    before = len(merged)
    added = skipped = dropped = 0
    for raw in incoming:
        rec = normalize_org(raw)
        if rec is None:
            dropped += 1
            continue
        url_dup = bool(rec["url"]) and _norm_url(rec["url"]) in seen_urls
        if url_dup or _dedup_key(rec) in seen_keys:
            skipped += 1
            continue
        merged.append(rec)
        if rec["url"]:
            seen_urls.add(_norm_url(rec["url"]))
        seen_keys.add(_dedup_key(rec))
        added += 1

    merged.sort(key=lambda r: (r["country"], r["org_type"], r["name"].lower()))
    return {"orgs": merged, "added": added, "skipped": skipped,
            "dropped": dropped, "before": before, "after": len(merged)}


def coverage(orgs: list[dict[str, Any]]) -> dict[str, Any]:
    """Country / org-type / contactability breakdown."""
    return {
        "total": len(orgs),
        "countries": sorted({o["country"] for o in orgs}),
        "n_countries": len({o["country"] for o in orgs}),
        "by_type": dict(Counter(o["org_type"] for o in orgs).most_common()),
        "url_verified": sum(1 for o in orgs if o["url_verified"]),
        "with_phone": sum(1 for o in orgs if o["contact_phone"]),
        "with_email": sum(1 for o in orgs if o["contact_email"]),
    }


def load_catalog(path: Path = _CATALOG) -> list[dict[str, Any]]:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("pyyaml required") from exc
    if not path.exists():
        return []
    return list((yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("orgs") or [])


def write_catalog(orgs: list[dict[str, Any]], path: Path = _CATALOG) -> None:
    import yaml
    header = {
        "catalog": "migrant_support_orgs",
        "purpose": ("Organisations that HELP migrant workers -- helplines, shelters, "
                    "legal aid, unions, resource centres, anti-trafficking NGOs, labour "
                    "attaches, intergovernmental + seafarer-welfare bodies. The protective "
                    "directory DueCare surfaces TO workers/caseworkers. Public org contact "
                    "info only (no individual PII)."),
        "orgs": orgs,
    }
    path.write_text(yaml.safe_dump(header, sort_keys=False, allow_unicode=False,
                                   width=100, default_flow_style=False), encoding="utf-8")


def _report(title: str, cov: dict) -> None:
    print(f"\n{title}: {cov['total']} orgs across {cov['n_countries']} countries/regions")
    print(f"  url_verified={cov['url_verified']}  with_phone={cov['with_phone']}  with_email={cov['with_email']}")
    print("  by type:")
    for t, n in cov["by_type"].items():
        print(f"    {t:22s} {n}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--incoming", type=Path, help="JSON of researched support orgs")
    ap.add_argument("--catalog", type=Path, default=_CATALOG)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args(argv)

    existing = load_catalog(args.catalog)
    incoming = _coerce(json.loads(args.incoming.read_text(encoding="utf-8"))) if args.incoming else []
    result = merge(existing, incoming)
    print(f"merge: before={result['before']} incoming={len(incoming)} added={result['added']} "
          f"skipped_dup={result['skipped']} dropped_unusable={result['dropped']} after={result['after']}")
    if args.report:
        if existing:
            _report("BEFORE", coverage([r for r in (normalize_org(x) for x in existing) if r]))
        _report("AFTER", coverage(result["orgs"]))
    if args.apply:
        write_catalog(result["orgs"], args.catalog)
        print(f"\nwrote {args.catalog}  ({result['after']} orgs)")
    else:
        print("\n(dry run -- pass --apply to write)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
