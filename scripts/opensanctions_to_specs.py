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


def drafts(sources: list[dict], *, existing_ids: set[str], categories: set[str] | None = None) -> list[dict]:
    """Build deduped draft specs, skipping ids already live and unsupported formats."""
    out: dict[str, dict] = {}
    for rec in sources:
        if categories and rec.get("category") not in categories:
            continue
        spec = to_draft_spec(rec)
        if spec and spec["id"] not in existing_ids and spec["id"] not in out:
            out[spec["id"]] = spec
    return sorted(out.values(), key=lambda s: s["id"])


def live_spec_ids(path: Path) -> set[str]:
    """Ids already onboarded in registry_specs.yaml (so drafts don't duplicate them)."""
    if not path.exists():
        return set()
    data = _yaml().safe_load(path.read_text(encoding="utf-8")) or {}
    return {str(s.get("id")) for s in data.get("specs", []) if isinstance(s, dict)}


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
    specs = drafts(sources, existing_ids=live_spec_ids(Path(args.specs)), categories=cats)
    summary = summarize(specs)

    print(f"{summary['drafts']} draft specs (need field-map verification before use)", file=sys.stderr)
    print("  by format:", summary["by_format"], "| by type:", summary["by_type"], file=sys.stderr)
    if args.stats:
        return 0

    out = _ROOT / args.out if not Path(args.out).is_absolute() else Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(_emit_yaml(specs), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size} bytes) -- DRAFTS, verify field maps before promoting")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
