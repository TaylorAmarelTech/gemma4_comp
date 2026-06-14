#!/usr/bin/env python3
"""Merge researched licensed-entity *registry sources* into the catalogue.

This is the reusable counterpart to the ad-hoc inline generation that first
produced ``configs/duecare/research_monitor/licensed_entity_sources.yaml``.
It takes a JSON payload of candidate registries (the shape a research swarm
returns -- ``{"registries": [...]}`` or a bare ``[...]``) and folds it into the
catalogue, deterministically and idempotently:

* country codes are upper-cased; industries are validated against a controlled
  vocabulary (unknown -> ``other``);
* ``entity_type`` is mapped from ``industry`` onto the 16 canonical entity_kb
  types, so a catalogued source can feed ``entity_kb`` ingestion later;
* every source gets a deterministic id ``<cc>_<industry[:14]>_<name-slug[:30]>``
  matching the ids already in the catalogue;
* duplicates are dropped by normalized URL *and* by id, so re-running a swarm
  never double-writes;
* text fields are sanitized -- smart punctuation folded to ASCII and the U+FFFD
  replacement character (the ``?`` mojibake already in a few rows) repaired
  to ``-`` -- so the YAML stays clean ASCII.

By default it is a DRY RUN: it prints what *would* change and writes nothing.
Pass ``--apply`` to write the catalogue back (it is a committed config file, not
a live knowledge surface, so writing it is the intended maintenance path).

Examples
--------
    # dry-run merge of a swarm result, with a coverage report
    python scripts/merge_entity_sources.py --incoming reports/_scratch/swarm.json --report

    # apply it
    python scripts/merge_entity_sources.py --incoming reports/_scratch/swarm.json --apply

    # just sanitize/normalize the existing catalogue in place (no new data)
    python scripts/merge_entity_sources.py --apply
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

_ROOT = Path(__file__).resolve().parents[1]
_CATALOG = _ROOT / "configs" / "duecare" / "research_monitor" / "licensed_entity_sources.yaml"

# ---------------------------------------------------------------------------
# Controlled vocabulary
# ---------------------------------------------------------------------------

#: Industries the catalogue recognises. Anything else collapses to ``other``.
INDUSTRIES: tuple[str, ...] = (
    "recruitment_agency", "manning_agency", "medical_clinic", "training_center",
    "money_lender", "financial_services", "remittance", "hotel",
    "security_services", "company_registry", "construction", "fishing_seafood",
    "manufacturing", "agriculture", "domestic_worker", "care_home",
    "facility_management", "other",
)

#: industry -> one of the 16 canonical ``entity_kb.ENTITY_TYPES``. Several
#: sector registries (construction, fishing, garment, farms, care homes,
#: cleaning) have no dedicated entity_kb type, so they resolve to ``company``;
#: domestic-worker placement agencies are recruiters.
IND2TYPE: dict[str, str] = {
    "recruitment_agency": "recruitment_agency",
    "manning_agency": "manning_agency",
    "medical_clinic": "medical_clinic",
    "training_center": "training_center",
    "money_lender": "lender",
    "financial_services": "financial_services",
    "remittance": "remittance",
    "hotel": "hotel",
    "security_services": "security_services",
    "company_registry": "company",
    "construction": "company",
    "fishing_seafood": "company",
    "manufacturing": "company",
    "agriculture": "company",
    "domestic_worker": "recruitment_agency",
    "care_home": "company",
    "facility_management": "company",
    "other": "company",
}

ACCESS_TIERS: tuple[str, ...] = ("free", "freemium", "login", "paid")

# ---------------------------------------------------------------------------
# Text hygiene
# ---------------------------------------------------------------------------

#: common smart punctuation + the lossy U+FFFD replacement char -> ASCII.
#: Anything else non-ASCII is dropped by the encode/ignore pass below.
_MOJIBAKE: tuple[tuple[str, str], ...] = (
    ("—", "-"), ("–", "-"), ("‒", "-"), ("−", "-"),
    ("‘", "'"), ("’", "'"), ("“", '"'), ("”", '"'),
    ("…", "..."), (" ", " "), ("­", ""),
    ("•", "-"), ("·", "-"),
    ("�", "-"),  # already-lossy replacement char -> dash (most were en-dashes)
)


def sanitize_text(value: str) -> str:
    """Fold smart punctuation / mojibake to ASCII and collapse whitespace.

    Args:
        value: arbitrary text (registry name, notes, ...).

    Returns:
        ASCII-clean, single-spaced text. The U+FFFD replacement char is
        repaired to ``-`` because the rows that already carry it lost an
        en-dash on the way in.
    """
    text = value or ""
    for bad, good in _MOJIBAKE:
        text = text.replace(bad, good)
    # any remaining non-ASCII -> drop, then tidy whitespace + dash runs
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s*-\s*-\s*", " - ", text)
    return text


def _slug(value: str, limit: int) -> str:
    """Lowercase ``value``, map non-alphanumerics to ``_``, trim to ``limit``."""
    s = re.sub(r"[^a-z0-9]+", "_", sanitize_text(value).lower()).strip("_")
    return s[:limit].strip("_")


def make_id(country: str, industry: str, name: str) -> str:
    """Deterministic catalogue id ``<cc>_<industry[:14]>_<name-slug[:30]>``."""
    cc = re.sub(r"[^a-z0-9]", "", (country or "xx").lower())[:2] or "xx"
    ind = re.sub(r"[^a-z0-9_]", "", (industry or "other").lower())[:14].strip("_")
    return f"{cc}_{ind}_{_slug(name, 30)}"


def _norm_url(url: str) -> str:
    """Normalize a URL for dedup: lowercase scheme+host, strip trailing slash."""
    u = (url or "").strip()
    m = re.match(r"(?i)^(https?://[^/]+)(/.*)?$", u)
    if not m:
        return u.rstrip("/").lower()
    host = m.group(1).lower()
    path = (m.group(2) or "").rstrip("/")
    return host + path


# ---------------------------------------------------------------------------
# Record normalization
# ---------------------------------------------------------------------------

_FIELDS = ("id", "name", "publisher", "url", "country", "industry", "entity_type",
           "access_tier", "official", "has_data_endpoint", "url_verified",
           "notes", "confidence")


def normalize_record(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Coerce a researched/raw registry dict into a canonical catalogue row.

    Returns ``None`` when the record has no usable URL or name (the two fields a
    source is useless without).
    """
    name = sanitize_text(str(raw.get("name") or "")).strip()
    url = str(raw.get("url") or "").strip()
    if not name or not url.lower().startswith("http"):
        return None

    industry = str(raw.get("industry") or "other").strip().lower()
    if industry not in INDUSTRIES:
        industry = "other"
    country = re.sub(r"[^A-Za-z]", "", str(raw.get("country") or "")).upper()[:2] or "XX"

    try:
        confidence = float(raw.get("confidence", 0.6))
    except (TypeError, ValueError):
        confidence = 0.6
    confidence = max(0.0, min(1.0, confidence))

    access = str(raw.get("access_tier") or "free").strip().lower()
    if access not in ACCESS_TIERS:
        access = "free"

    rec = {
        "id": str(raw.get("id") or "").strip() or make_id(country, industry, name),
        "name": name,
        "publisher": sanitize_text(str(raw.get("publisher") or "")).strip(),
        "url": url,
        "country": country,
        "industry": industry,
        "entity_type": IND2TYPE.get(industry, "company"),
        "access_tier": access,
        "official": bool(raw.get("official", True)),
        "has_data_endpoint": bool(raw.get("has_data_endpoint", False)),
        "url_verified": bool(raw.get("url_verified", False)),
        "notes": sanitize_text(str(raw.get("notes") or "")).strip()[:600],
        "confidence": round(confidence, 2),
    }
    return {k: rec[k] for k in _FIELDS}


def _coerce_incoming(payload: Any) -> list[dict[str, Any]]:
    """Accept ``{"registries": [...]}``, ``{"sources": [...]}`` or a bare list."""
    if isinstance(payload, dict):
        for key in ("registries", "sources", "records", "results"):
            if isinstance(payload.get(key), list):
                return [x for x in payload[key] if isinstance(x, dict)]
        return []
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    return []


# ---------------------------------------------------------------------------
# Merge
# ---------------------------------------------------------------------------

def merge(existing: Iterable[dict[str, Any]],
          incoming: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Fold ``incoming`` registries into ``existing``, deduped and sorted.

    Existing rows are re-normalized (so mojibake gets repaired in place). A new
    row is skipped when its normalized URL or its id already appears.

    Returns a dict with ``sources`` (the merged, sorted list), ``added``,
    ``skipped`` (duplicates), ``dropped`` (unusable), and ``before``/``after``
    counts.
    """
    merged: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    seen_ids: set[str] = set()

    for raw in existing:
        rec = normalize_record(raw)
        if rec is None:
            continue
        merged.append(rec)
        seen_urls.add(_norm_url(rec["url"]))
        seen_ids.add(rec["id"])

    before = len(merged)
    added = skipped = dropped = 0
    for raw in incoming:
        rec = normalize_record(raw)
        if rec is None:
            dropped += 1
            continue
        if _norm_url(rec["url"]) in seen_urls or rec["id"] in seen_ids:
            skipped += 1
            continue
        merged.append(rec)
        seen_urls.add(_norm_url(rec["url"]))
        seen_ids.add(rec["id"])
        added += 1

    merged.sort(key=lambda r: (r["country"], r["industry"], r["name"].lower()))
    return {"sources": merged, "added": added, "skipped": skipped,
            "dropped": dropped, "before": before, "after": len(merged)}


def coverage(sources: list[dict[str, Any]]) -> dict[str, Any]:
    """Country / industry / verification breakdown for a sources list."""
    return {
        "total": len(sources),
        "countries": sorted({s["country"] for s in sources}),
        "n_countries": len({s["country"] for s in sources}),
        "by_industry": dict(Counter(s["industry"] for s in sources).most_common()),
        "official": sum(1 for s in sources if s["official"]),
        "url_verified": sum(1 for s in sources if s["url_verified"]),
        "with_data_endpoint": sum(1 for s in sources if s["has_data_endpoint"]),
    }


# ---------------------------------------------------------------------------
# YAML IO
# ---------------------------------------------------------------------------

def load_catalog(path: Path = _CATALOG) -> list[dict[str, Any]]:
    """Load the catalogue's ``sources`` list (``[]`` if absent)."""
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - env guard
        raise SystemExit("pyyaml required: pip install pyyaml") from exc
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return list(data.get("sources") or [])


def write_catalog(sources: list[dict[str, Any]], path: Path = _CATALOG,
                  *, meta: dict[str, Any] | None = None) -> None:
    """Write the catalogue YAML (ASCII, deterministic field order)."""
    import yaml

    header = {
        "catalog": "licensed_entity_sources",
        "purpose": ("Official registries of licensed entities across migration "
                    "countries and trafficking-relevant industries. SOURCES ONLY "
                    "- pointers to public/official registries, no scraped PII. "
                    "Fed into the acquisition cascade via --registry <id>."),
        **(meta or {}),
        "sources": sources,
    }
    text = yaml.safe_dump(header, sort_keys=False, allow_unicode=False,
                          width=100, default_flow_style=False)
    path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _print_report(title: str, cov: dict[str, Any]) -> None:
    print(f"\n{title}: {cov['total']} sources across {cov['n_countries']} countries")
    print(f"  official={cov['official']}  url_verified={cov['url_verified']}  "
          f"with_data_endpoint={cov['with_data_endpoint']}")
    print(f"  countries: {' '.join(cov['countries'])}")
    print("  by industry:")
    for ind, n in cov["by_industry"].items():
        print(f"    {ind:20s} {n}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--incoming", type=Path,
                    help="JSON file of candidate registries to merge in")
    ap.add_argument("--catalog", type=Path, default=_CATALOG)
    ap.add_argument("--apply", action="store_true",
                    help="write the catalogue back (default is a dry run)")
    ap.add_argument("--report", action="store_true",
                    help="print before/after coverage breakdown")
    args = ap.parse_args(argv)

    existing = load_catalog(args.catalog)
    incoming: list[dict[str, Any]] = []
    if args.incoming:
        incoming = _coerce_incoming(json.loads(args.incoming.read_text(encoding="utf-8")))

    result = merge(existing, incoming)
    print(f"merge: before={result['before']} incoming={len(incoming)} "
          f"added={result['added']} skipped_dup={result['skipped']} "
          f"dropped_unusable={result['dropped']} after={result['after']}")

    if args.report:
        if existing:
            _print_report("BEFORE", coverage([r for r in (normalize_record(x)
                          for x in existing) if r]))
        _print_report("AFTER", coverage(result["sources"]))

    if args.apply:
        write_catalog(result["sources"], args.catalog)
        print(f"\nwrote {args.catalog}  ({result['after']} sources)")
    else:
        print("\n(dry run -- pass --apply to write)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
