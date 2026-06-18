#!/usr/bin/env python3
"""Harvest OpenSanctions dataset metadata into our source catalog (propose-only).

OpenSanctions (``opensanctions/opensanctions``, MIT code) maintains hundreds of
per-registry crawler definitions under ``datasets/<cc>/<name>/<name>.yml``. Each YAML
names a real, official SOURCE: its landing ``url``, its ``data.url`` + ``data.format``
endpoint, the ``publisher`` (with an ``official`` flag and country), update frequency,
and classifying ``tags`` (``list.sanction`` / ``list.pep`` / ``list.debarment`` /
``reg.warn`` / ...).

That curated SOURCE LIST -- not the sanctions data itself -- is the asset: a
ready-made directory of government registries and screening lists across ~97
countries we can fold into our own licensed-entity / screening catalogs.

This tool PORTS the source list. It reads the metadata YAMLs (from a local clone of
opensanctions, or via an injected fetcher), maps each to our catalog-source shape,
classifies it (registry / sanctions / pep / debarment / regulatory), and writes a
PROPOSE-ONLY staging file under ``reports/``. It never touches the live catalog and
never downloads the sanctions data -- merging is a separate explicit step
(``scripts/merge_entity_sources.py``).

License note: opensanctions CODE/metadata is MIT; the consolidated DATA is CC-BY-NC.
We consume only the metadata (source pointers) here -- no entity data is fetched.

Usage:
    # clone once:  gh repo clone opensanctions/opensanctions ../opensanctions
    python scripts/harvest_opensanctions_sources.py --clone ../opensanctions \
        --out reports/opensanctions_sources/proposed_sources.yaml
    python scripts/harvest_opensanctions_sources.py --clone ../opensanctions --country ph --stats
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable, Iterator

_ROOT = Path(__file__).resolve().parents[1]

#: tag prefix -> our category (first match wins, most-specific first)
_TAG_CATEGORY: list[tuple[str, str]] = [
    ("list.debarment", "debarment"),
    ("list.sanction", "sanctions"),
    ("sanction", "sanctions"),
    ("list.pep", "pep"),
    ("role.pep", "pep"),
    ("reg.warn", "regulatory"),
    ("reg.action", "regulatory"),
    ("list.regulatory", "regulatory"),
    ("poi", "watchlist"),
]
#: title keywords that mark an actual licensed-entity register (over a watchlist)
_REGISTRY_WORDS = ("compan", "registr", "register", "procurement", "licen",
                   "incorporat", "business", "supplier")
#: category -> (industry, entity_type) in our taxonomy
_CATEGORY_MAP: dict[str, tuple[str, str]] = {
    "debarment": ("debarment_list", "company"),
    "sanctions": ("sanctions_list", "sanctioned_entity"),
    "pep": ("pep_list", "individual"),
    "regulatory": ("financial_regulator", "company"),
    "registry": ("company_registry", "company"),
    "watchlist": ("watchlist", "entity"),
    "other": ("watchlist", "entity"),
}


def _yaml_load(text: str) -> dict:
    """Parse one metadata YAML (PyYAML; empty dict on failure)."""
    try:
        import yaml
    except ModuleNotFoundError as exc:  # pragma: no cover - venv has pyyaml
        raise SystemExit("PyYAML required: pip install pyyaml") from exc
    data = yaml.safe_load(text) or {}
    return data if isinstance(data, dict) else {}


def classify(meta: dict) -> str:
    """Category from the dataset's tags, then title keywords, else 'other'."""
    tags = [str(t).lower() for t in (meta.get("tags") or [])]
    for prefix, cat in _TAG_CATEGORY:
        if any(t == prefix or t.startswith(prefix) for t in tags):
            # a debarment/sanction list that is really a *register* stays a register
            if cat in ("watchlist",) and _looks_like_registry(meta):
                return "registry"
            return cat
    if _looks_like_registry(meta):
        return "registry"
    return "other"


def _looks_like_registry(meta: dict) -> bool:
    title = str(meta.get("title") or "").lower()
    return any(w in title for w in _REGISTRY_WORDS)


_SLUG = re.compile(r"[^a-z0-9]+")


def _slugify(text: str, n: int) -> str:
    return _SLUG.sub("_", str(text).lower()).strip("_")[:n].strip("_")


def make_id(region: str, name: str, industry: str) -> str:
    """``<cc>_<industry14>_<name30>`` -- same shape as the live catalog ids."""
    cc = _slugify(region, 8) or "xx"
    return f"{cc}_{_slugify(industry, 14)}_{_slugify(name, 30)}"


def to_record(meta: dict, *, region: str) -> dict | None:
    """Map one OpenSanctions metadata dict to a catalog-source record.

    Returns ``None`` for entries that are not a real external source -- collections
    and aggregations carry no ``publisher`` and no ``title``/``url`` of their own.
    """
    if not isinstance(meta, dict):
        return None
    publisher = meta.get("publisher")
    title = str(meta.get("title") or "").strip()
    if not isinstance(publisher, dict) or not title:
        return None  # collection / meta dataset -- no concrete source to port

    category = classify(meta)
    industry, entity_type = _CATEGORY_MAP.get(category, _CATEGORY_MAP["other"])

    data = meta.get("data") if isinstance(meta.get("data"), dict) else {}
    data_url = str(data.get("url") or "").strip()
    data_format = str(data.get("format") or "").strip()
    country = str(publisher.get("country") or region or "").strip() or region
    pub_name = str(publisher.get("name") or "").strip()
    acronym = str(publisher.get("acronym") or "").strip()
    publisher_label = f"{pub_name} ({acronym})" if acronym and acronym not in pub_name else pub_name

    freq = ""
    cov = meta.get("coverage")
    if isinstance(cov, dict):
        freq = str(cov.get("frequency") or "").strip()
    summary = " ".join(str(meta.get("summary") or "").split())
    tags = ", ".join(str(t) for t in (meta.get("tags") or []))

    note = (
        f"{summary} | category={category}; "
        f"endpoint={data_url or 'n/a'} ({data_format or 'n/a'}); "
        f"update={freq or 'n/a'}; tags=[{tags}]. "
        "Source pointer ported from opensanctions/opensanctions (MIT metadata); "
        "no entity data fetched."
    ).strip()

    return {
        "id": make_id(country, title, industry),
        "name": title,
        "publisher": publisher_label or "OpenSanctions-listed publisher",
        "url": str(meta.get("url") or publisher.get("url") or "").strip(),
        "country": country.upper(),
        "industry": industry,
        "entity_type": entity_type,
        "access_tier": "free",
        "official": bool(publisher.get("official")),
        "has_data_endpoint": bool(data_url),
        "url_verified": False,
        "notes": note,
        "confidence": 0.85,  # curated, official source list -- but URL unverified by us
        # extras (kept for routing/merge; harmless to the catalog schema)
        "category": category,
        "data_url": data_url,
        "data_format": data_format,
    }


def harvest(items: Iterable[tuple[str, str]]) -> list[dict]:
    """``(region, yaml_text)`` pairs -> deduped catalog records (by id)."""
    out: dict[str, dict] = {}
    for region, text in items:
        rec = to_record(_yaml_load(text), region=region)
        if rec and rec["id"] not in out:
            out[rec["id"]] = rec
    return sorted(out.values(), key=lambda r: (r["country"], r["category"], r["name"]))


def iter_clone(root: Path, *, country: str | None = None,
               skip_thematic: bool = False) -> Iterator[tuple[str, str]]:
    """Walk ``datasets/<region>/<name>/*.yml`` in a local opensanctions clone."""
    base = Path(root)
    ds = base / "datasets" if (base / "datasets").is_dir() else base
    for region_dir in sorted(p for p in ds.iterdir() if p.is_dir()):
        region = region_dir.name
        if country and region != country.lower():
            continue
        if skip_thematic and region.startswith("_"):
            continue
        for yml in sorted(region_dir.rglob("*.yml")):
            try:
                yield region, yml.read_text(encoding="utf-8")
            except OSError:
                continue


def summarize(records: list[dict]) -> dict:
    """Counts by category and by country (+ how many carry a data endpoint)."""
    return {
        "total": len(records),
        "with_endpoint": sum(1 for r in records if r["has_data_endpoint"]),
        "official": sum(1 for r in records if r["official"]),
        "by_category": dict(Counter(r["category"] for r in records).most_common()),
        "by_country": dict(Counter(r["country"] for r in records).most_common(25)),
    }


def _emit_yaml(records: list[dict]) -> str:
    import yaml
    catalog = {
        "catalog": "opensanctions_ported_sources",
        "purpose": (
            "Government registries and screening lists ported (source pointers only) "
            "from opensanctions/opensanctions dataset metadata (MIT). PROPOSE-ONLY -- "
            "review then merge into licensed_entity_sources.yaml via merge_entity_sources.py. "
            "No OpenSanctions entity data is included (that data is CC-BY-NC)."
        ),
        "sources": records,
    }
    return yaml.safe_dump(catalog, sort_keys=False, allow_unicode=True, width=100)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--clone", required=True,
                    help="path to a local clone of opensanctions/opensanctions")
    ap.add_argument("--country", help="ISO dir to limit to (e.g. ph, hk, _global)")
    ap.add_argument("--skip-thematic", action="store_true",
                    help="skip _global/_collections/_externals dirs")
    ap.add_argument("--out", default="reports/opensanctions_sources/proposed_sources.yaml",
                    help="propose-only output path (under reports/, gitignored)")
    ap.add_argument("--stats", action="store_true", help="print a summary, don't write")
    args = ap.parse_args(argv)

    root = Path(args.clone)
    if not root.exists():
        ap.error(f"clone path not found: {root}\n"
                 "  gh repo clone opensanctions/opensanctions ../opensanctions")

    records = harvest(iter_clone(root, country=args.country, skip_thematic=args.skip_thematic))
    summary = summarize(records)

    print(f"harvested {summary['total']} source pointers "
          f"({summary['with_endpoint']} with a data endpoint, {summary['official']} official)",
          file=sys.stderr)
    print("  by category:", summary["by_category"], file=sys.stderr)

    if args.stats:
        print("  by country:", summary["by_country"], file=sys.stderr)
        return 0

    out = _ROOT / args.out if not Path(args.out).is_absolute() else Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(_emit_yaml(records), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size} bytes) -- PROPOSE-ONLY, review before merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
