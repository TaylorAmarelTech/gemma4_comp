#!/usr/bin/env python3
"""Scaffold draft registry-resolver specs from the harvested OpenSanctions sources.

The harvest (scripts/harvest_opensanctions_sources.py) gives, per source, a real
``data_url`` + ``data_format`` -- but NOT the field map (that lives in OpenSanctions'
crawler.py, not its metadata). So this tool produces **draft** ``registry_specs.yaml``
blocks with everything it can fill deterministically (url / format / entity_type /
jurisdiction / source) and leaves ``fields:`` as an explicit ``TODO`` plus
``_needs_verification: true``. A draft becomes a runnable spec only after someone
fetches the endpoint, reads the real keys, and fills the field map -- exactly how
ph_gppb_blacklist / si_kpk_business_restrictions / br_bcb_disqualified were promoted.

It is PROPOSE-ONLY: writes to reports/ (gitignored), skips ids already present in the
live registry_specs.yaml, and never fabricates a field map. Drafts are a verification
WORK-QUEUE, not onboarded specs.

Two onboarding paths from OpenSanctions:
  1. METADATA source-pointers (this tool) -- MIT metadata -> draft specs for the
     PRIMARY government endpoint; license-clean, the default.
  2. DATA datasets -- a few high-value OpenSanctions DATA exports are onboarded directly
     as VERIFIED specs that pull ``targets.simple.csv`` (CC-BY-NC; underlying gov list
     public domain; non-commercial use). Currently: ``us_cbp_forced_labor`` (CBP WRO &
     Findings, 59) and ``us_dhs_uflpa`` (UFLPA Entity List, 144) in registry_specs.yaml.

Usage:
    python scripts/opensanctions_to_specs.py --stats
    python scripts/opensanctions_to_specs.py --category registry,debarment,regulatory \
        --out reports/opensanctions_sources/draft_specs.yaml
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_HARVEST = _ROOT / "reports" / "opensanctions_sources" / "proposed_sources.yaml"
_LIVE_SPECS = _ROOT / "configs" / "duecare" / "research_monitor" / "registry_specs.yaml"

#: OpenSanctions data.format -> our registry_parsers format (None => unsupported, skip)
_FORMAT = {
    "json": "json", "csv": "csv", "xlsx": "xlsx", "xls": "xlsx",
    "html": "html_table", "pdf": "pdf_table",
}
_SLUG = re.compile(r"[^a-z0-9]+")


def _yaml():
    try:
        import yaml
        return yaml
    except ModuleNotFoundError as exc:  # pragma: no cover - venv has pyyaml
        raise SystemExit("PyYAML required: pip install pyyaml") from exc


def map_format(data_format: str) -> str | None:
    """OpenSanctions format string -> our parser format, or None if unsupported."""
    return _FORMAT.get(str(data_format or "").strip().lower())


def draft_spec_id(rec: dict) -> str:
    """Stable, readable draft id: ``os_<cc>_<name-slug>`` (prefix marks the origin)."""
    cc = _SLUG.sub("_", str(rec.get("country") or "xx").lower()).strip("_")[:6] or "xx"
    name = _SLUG.sub("_", str(rec.get("name") or "").lower()).strip("_")[:28].strip("_")
    return f"os_{cc}_{name}"


def to_draft_spec(rec: dict) -> dict | None:
    """One harvest record -> a draft spec dict, or None if it has no usable endpoint."""
    fmt = map_format(rec.get("data_format", ""))
    url = str(rec.get("data_url") or "").strip()
    if not fmt or not url:
        return None
    return {
        "id": draft_spec_id(rec),
        "url": url,
        "format": fmt,
        "entity_type": rec.get("entity_type") or "entity",
        "jurisdiction": str(rec.get("country") or "").strip(),
        "_needs_verification": True,
        "fields": {"name": "TODO: fetch endpoint and map the entity-name key"},
        "source": f"{rec.get('name', '')} [{rec.get('category', '')}] -- {rec.get('publisher', '')}",
    }


def drafts(sources: list[dict], *, existing_ids: set[str], existing_urls: set[str] = frozenset(),
           categories: set[str] | None = None) -> list[dict]:
    """Build deduped draft specs, skipping unsupported formats and anything already live.

    A draft is dropped if its id OR its url is already onboarded -- the url check means a
    promoted endpoint leaves the queue even when its spec id was renamed on promotion.
    """
    out: dict[str, dict] = {}
    for rec in sources:
        if categories and rec.get("category") not in categories:
            continue
        spec = to_draft_spec(rec)
        if not spec or spec["id"] in existing_ids or spec["id"] in out or spec["url"] in existing_urls:
            continue
        out[spec["id"]] = spec
    return sorted(out.values(), key=lambda s: s["id"])


def _live_specs(path: Path) -> list[dict]:
    if not path.exists():
        return []
    data = _yaml().safe_load(path.read_text(encoding="utf-8")) or {}
    return [s for s in data.get("specs", []) if isinstance(s, dict)]


def live_spec_ids(path: Path) -> set[str]:
    """Ids already onboarded in registry_specs.yaml (so drafts don't duplicate them)."""
    return {str(s.get("id")) for s in _live_specs(path)}


def live_spec_urls(path: Path) -> set[str]:
    """Urls already onboarded -- drops a promoted endpoint from the queue even if its
    spec id was renamed during promotion."""
    return {str(s.get("url")) for s in _live_specs(path) if s.get("url")}


#: OpenSanctions DATA datasets onboarded directly as verified specs (path 2 -- they pull
#: the CC-BY-NC targets.simple.csv export, not the MIT metadata source-pointer). These are
#: NOT in the draft queue; they live in registry_specs.yaml as runnable specs.
DATA_DATASET_SPEC_IDS = ("us_cbp_forced_labor", "us_dhs_uflpa")


def data_dataset_specs(path: Path) -> list[dict]:
    """The onboarded OpenSanctions DATA-dataset specs, read from registry_specs.yaml.

    Single source of truth -- this reflects what is actually in the live specs file, so the
    tool reports the CBP / UFLPA onboarding rather than hardcoding a duplicate copy.
    """
    return [s for s in _live_specs(path) if str(s.get("id")) in DATA_DATASET_SPEC_IDS]


def summarize(specs: list[dict]) -> dict:
    return {
        "drafts": len(specs),
        "by_format": dict(Counter(s["format"] for s in specs).most_common()),
        "by_type": dict(Counter(s["entity_type"] for s in specs).most_common()),
    }


def _emit_yaml(specs: list[dict]) -> str:
    catalog = {
        "catalog": "opensanctions_draft_specs",
        "purpose": (
            "DRAFT registry-resolver specs scaffolded from harvested OpenSanctions "
            "endpoints. NOT runnable: each 'fields' map is a TODO until the endpoint is "
            "fetched and its keys are mapped. Verification work-queue -- promote into "
            "registry_specs.yaml one at a time after authoring + testing the field map."
        ),
        "specs": specs,
    }
    return _yaml().safe_dump(catalog, sort_keys=False, allow_unicode=True, width=100)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--harvest", default=str(_HARVEST), help="harvested sources YAML")
    ap.add_argument("--specs", default=str(_LIVE_SPECS), help="live registry_specs.yaml (ids to skip)")
    ap.add_argument("--category", help="comma list to keep (e.g. registry,debarment,regulatory)")
    ap.add_argument("--out", default="reports/opensanctions_sources/draft_specs.yaml")
    ap.add_argument("--stats", action="store_true", help="print a summary, don't write")
    args = ap.parse_args(argv)

    hp = Path(args.harvest)
    if not hp.exists():
        ap.error(f"harvest not found: {hp}\n  run scripts/harvest_opensanctions_sources.py first")
    sources = (_yaml().safe_load(hp.read_text(encoding="utf-8")) or {}).get("sources", [])
    cats = {c.strip() for c in args.category.split(",")} if args.category else None
    live = Path(args.specs)
    specs = drafts(sources, existing_ids=live_spec_ids(live), existing_urls=live_spec_urls(live),
                   categories=cats)
    summary = summarize(specs)

    onboarded = data_dataset_specs(live)
    print(f"{summary['drafts']} draft specs (need field-map verification before use)", file=sys.stderr)
    print("  by format:", summary["by_format"], "| by type:", summary["by_type"], file=sys.stderr)
    if onboarded:
        print(f"  OpenSanctions data-datasets already onboarded as verified specs: "
              f"{', '.join(s['id'] for s in onboarded)}", file=sys.stderr)
    if args.stats:
        return 0

    out = _ROOT / args.out if not Path(args.out).is_absolute() else Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(_emit_yaml(specs), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size} bytes) -- DRAFTS, verify field maps before promoting")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
