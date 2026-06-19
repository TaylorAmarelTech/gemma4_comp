#!/usr/bin/env python3
"""Cluster the cascade registries through entity_link -> one LEI-keyed entity view.

Each onboarded registry (registry_specs + the deterministic resolvers) is a separate
list that names entities its own way. This orchestrator resolves them, pools every
entity (tagged with its source registry), and runs the splink dedupe/cluster model
(``entity_link.cluster_entities``) so the same real-world entity collapses into one
cluster across sources. The high-value output is the **cross-source clusters** -- an
entity that appears in two or more registries (e.g. a company on both a debarment list
and a sanctions list).

Fault-isolated (a registry that fails to resolve is skipped, not fatal), bounded
(``--cap`` per registry), and propose-only (writes a cluster report under reports/,
never mutates the live KB). Browser-only presets (dmw_lra) are not resolvable here and
are skipped automatically.

Usage:
    python scripts/cluster_registries.py --cap 3000
    python scripts/cluster_registries.py --registries ofac_sdn,afdb_debarred,us_dod_chinese_military
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _sibling(name: str):
    spec = importlib.util.spec_from_file_location(name, _ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def default_resolver():
    """A ``resolve(id) -> [records]`` backed by the acquisition cascade (all 30 registries)."""
    for dep in ("registry_parsers", "registry_spec"):
        _sibling(dep)
    ac = _sibling("acquisition_cascade")

    def resolve(rid: str) -> list[dict]:
        result = ac.REGISTRY_RESOLVERS[rid]({"url": "", "preset": rid})
        return list(result.get("records") or [])
    return resolve, sorted(ac.REGISTRY_RESOLVERS)


def resolve_pool(ids: list[str], *, cap: int, resolve) -> list[dict]:
    """Resolve every registry, cap each, tag source -- skipping any that fail."""
    pool: list[dict] = []
    for rid in ids:
        try:
            recs = resolve(rid)
        except Exception as exc:  # noqa: BLE001 - one bad registry must not stop the rest
            print(f"  skip {rid}: {type(exc).__name__}: {str(exc)[:60]}", file=sys.stderr)
            continue
        recs = recs[:cap] if cap else recs
        for r in recs:
            r = dict(r)
            r["source"] = rid
            pool.append(r)
        print(f"  {rid}: {len(recs)}", file=sys.stderr)
    return pool


def report(clusters: list[dict], n_pool: int, el) -> dict:
    """Summary: dedup reduction + cross-source / LEI-stamped cluster counts."""
    cross = el.cross_source_clusters(clusters)
    return {
        "entities": n_pool,
        "clusters": len(clusters),
        "dedup_removed": n_pool - len(clusters),
        "cross_source_clusters": len(cross),
        "lei_clusters": sum(1 for c in clusters if c["lei"]),
        "max_sources_in_a_cluster": max((c["n_sources"] for c in clusters), default=0),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--registries", help="comma list of registry ids (default: all resolvable)")
    ap.add_argument("--cap", type=int, default=3000, help="max entities per registry (default 3000)")
    ap.add_argument("--threshold", type=float, default=0.92, help="cluster match-probability threshold")
    ap.add_argument("--out", default="reports/entity_kb/registry_clusters.jsonl",
                    help="propose-only cluster JSONL (under reports/)")
    args = ap.parse_args(argv)

    resolve, all_ids = default_resolver()
    ids = [s.strip() for s in args.registries.split(",")] if args.registries else all_ids
    print(f"resolving {len(ids)} registries (cap {args.cap})...", file=sys.stderr)
    pool = resolve_pool(ids, cap=args.cap, resolve=resolve)
    if not pool:
        ap.error("no entities resolved")

    el = _sibling("entity_link")
    print(f"clustering {len(pool)} entities...", file=sys.stderr)
    clusters = el.cluster_entities(pool, threshold=args.threshold)
    summary = report(clusters, len(pool), el)
    print(f"summary: {summary}", file=sys.stderr)

    cross = el.cross_source_clusters(clusters)
    print(f"\ntop cross-source clusters ({len(cross)}):", file=sys.stderr)
    for c in cross[:12]:
        print(f"  [{'+'.join(c['sources'])}] {c['names'][0][:46]}"
              f"{' lei='+c['lei'] if c['lei'] else ''}", file=sys.stderr)

    out = _ROOT / args.out if not Path(args.out).is_absolute() else Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(json.dumps(c, ensure_ascii=False) for c in clusters), encoding="utf-8")
    print(f"\nwrote {out} ({len(clusters)} clusters) -- PROPOSE-ONLY", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
