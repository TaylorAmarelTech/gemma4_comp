#!/usr/bin/env python3
"""Unify every relationship edge the entity-intelligence connectors emit into ONE graph file.

The connectors each stage their own propose-only edges under ``reports/entity_kb/``:

  * ``gleif_rr``           -> ``parent_of``        (GLEIF Level-2 RR ownership tree)
  * ``openownership_bods`` -> ``owns_or_controls`` (beneficial-ownership statements)
  * ``domain_intel``       -> ``registers`` / ``registrar_of`` / ``admin_of`` / ``tech_of``
                              (RDAP) and ``hosted_on`` / ``mail_via`` (DNS)
  * ``entity_link``        -> clusters, which become ``same_as`` edges here

This module collects those, normalises them to ONE canonical edge shape, synthesises
registry ``registers`` edges from entity records (authority --registers--> licensed entity),
dedups (keeping the higher-weight edge and unioning sources), and exports a single
``edges.jsonl`` plus a by-predicate / by-source manifest -- so the whole entity graph is one
file a human (or a graph loader / the render graph view) can review in one place.

Propose-only: reads + writes only under ``reports/``; never mutates the live knowledge layer.

Canonical edge: ``{subject_id, predicate, object_id, source, weight, qualifier}``.

Usage:
    python scripts/entity_edges.py                      # reports/entity_kb/*.jsonl -> edges.jsonl
    python scripts/entity_edges.py --from-reports DIR --out DIR/edges.jsonl
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from collections import Counter
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_DIR = _ROOT / "reports" / "entity_kb"

#: predicate -> one-line direction note (forward-compatible: unknown predicates still pass
#: through normalise; this is documentation + the manifest's known/unknown split).
KNOWN_PREDICATES = {
    "parent_of": "subject (parent) controls object (subsidiary) -- GLEIF Level-2 RR",
    "owns_or_controls": "subject (owner / interested party) owns or controls object -- BODS",
    "registers": "subject (registry / authority / registrant) lists or registers object",
    "registrar_of": "subject (registrar) registered object (domain) -- RDAP",
    "admin_of": "subject is the administrative contact for object (domain) -- RDAP",
    "tech_of": "subject is the technical contact for object (domain) -- RDAP",
    "hosted_on": "subject (domain) is served by object (nameserver) -- DNS",
    "mail_via": "subject (domain) routes mail through object (MX host) -- DNS",
    "same_as": "subject and object are the same real-world entity -- entity_link cluster",
}

#: files in the reports dir that are NOT edge/entity inputs to re-fold
_EXCLUDE = ("combined.jsonl", "edges.jsonl", "_combined_in.jsonl")


def normalize_edge(raw: dict, *, default_source: str = "", default_weight: float = 0.5) -> dict | None:
    """Coerce any connector edge dict to the canonical shape, or None if it is not an edge.

    Requires non-empty ``subject_id`` / ``predicate`` / ``object_id``; clamps weight to
    ``[0, 1]``; guarantees a dict ``qualifier``. Unknown predicates are kept (forward-compat)."""
    if not isinstance(raw, dict):
        return None
    s = str(raw.get("subject_id") or "").strip()
    p = str(raw.get("predicate") or "").strip()
    o = str(raw.get("object_id") or "").strip()
    if not (s and p and o):
        return None
    try:
        w = float(raw.get("weight", default_weight))
    except (TypeError, ValueError):
        w = default_weight
    w = max(0.0, min(1.0, w))
    q = raw.get("qualifier")
    return {"subject_id": s, "predicate": p, "object_id": o,
            "source": str(raw.get("source") or default_source),
            "weight": w, "qualifier": q if isinstance(q, dict) else {}}


def _edge_key(e: dict) -> tuple:
    """Dedup identity: same triple + same qualifier collapses; different qualifier survives."""
    return (e["subject_id"], e["predicate"], e["object_id"],
            json.dumps(e.get("qualifier") or {}, sort_keys=True, ensure_ascii=False))


def registers_edges(entity_records, *, source_key: str = "source", weight: float = 0.6) -> list[dict]:
    """Synthesise ``authority --registers--> entity`` edges from entity records.

    Object id is the entity's most stable native identifier (LEI if present, else the name)
    so these join the LEI-keyed ``parent_of`` edges. A ``kind=registry_listing`` qualifier
    distinguishes them from RDAP ``registers`` (registrant) edges."""
    out: list[dict] = []
    for r in entity_records or []:
        if not isinstance(r, dict):
            continue
        name = str(r.get("name") or "").strip()
        reg = str(r.get(source_key) or "").strip()
        if not (name and reg):
            continue
        oid = str(r.get("lei") or r.get("leiCode") or name)
        qual = {"kind": "registry_listing"}
        qual.update({k: r[k] for k in ("entity_type", "jurisdiction", "status") if r.get(k)})
        out.append({"subject_id": reg, "predicate": "registers", "object_id": oid,
                    "source": reg, "weight": weight, "qualifier": qual})
    return out


def same_as_edges(clusters, *, weight: float = 0.95) -> list[dict]:
    """entity_link clusters -> ``same_as`` edges from each cluster's canonical id to the rest.

    Uses the cluster's propagated ``lei`` (preferred canonical) + ``names``; only multi-id
    clusters emit edges."""
    out: list[dict] = []
    for c in clusters or []:
        if not isinstance(c, dict):
            continue
        lei = str(c.get("lei") or "")
        ids, seen = [], set()
        for x in ([lei] if lei else []) + [str(n) for n in (c.get("names") or [])]:
            if x and x not in seen:
                seen.add(x)
                ids.append(x)
        if len(ids) < 2:
            continue
        canon = ids[0]
        for other in ids[1:]:
            out.append({"subject_id": canon, "predicate": "same_as", "object_id": other,
                        "source": "entity_link cluster", "weight": weight,
                        "qualifier": {"cluster_id": str(c.get("cluster_id", "")),
                                      "n_sources": c.get("n_sources", 0)}})
    return out


def merge_edges(*edge_iterables, default_source: str = "") -> list[dict]:
    """Normalise + dedup edges from any number of sources into one stable-sorted list.

    On a key collision (same triple + qualifier) the higher-weight edge wins and the two
    sources are unioned, so re-running over overlapping inputs is idempotent."""
    best: dict[tuple, dict] = {}
    for it in edge_iterables:
        for raw in (it or []):
            e = normalize_edge(raw, default_source=default_source)
            if e is None:
                continue
            k = _edge_key(e)
            cur = best.get(k)
            if cur is None:
                best[k] = e
                continue
            srcs = sorted({s for s in (cur["source"], e["source"]) if s})
            winner = dict(e if e["weight"] >= cur["weight"] else cur)
            winner["source"] = " | ".join(srcs) if len(srcs) > 1 else (srcs[0] if srcs else "")
            best[k] = winner
    return sorted(best.values(),
                  key=lambda e: (e["predicate"], str(e["subject_id"]), str(e["object_id"])))


def node_set(edges) -> list[str]:
    """Sorted unique node ids referenced by any edge endpoint."""
    nodes: set[str] = set()
    for e in edges:
        nodes.add(e["subject_id"])
        nodes.add(e["object_id"])
    return sorted(nodes)


def build_manifest(edges) -> dict:
    """By-predicate / by-source counts + node/edge totals; flags any unknown predicate."""
    preds = Counter(e["predicate"] for e in edges)
    return {"_synthetic": False, "n_edges": len(edges), "n_nodes": len(node_set(edges)),
            "by_predicate": dict(preds), "by_source": dict(Counter(e["source"] for e in edges)),
            "unknown_predicates": sorted(p for p in preds if p not in KNOWN_PREDICATES)}


def load_edge_files(reports_dir, *, exclude=_EXCLUDE) -> tuple[list[dict], list[dict]]:
    """Read every ``*.jsonl`` under ``reports_dir`` -> ``(edges, entity_records)``.

    Tolerates three line shapes: a flat edge (has subject_id+object_id); a nested
    ``{edges:[...], entities:[...]}`` record (domain_intel); and a plain entity record
    (has ``name``, no subject_id). Bad JSON lines are skipped."""
    edges: list[dict] = []
    ents: list[dict] = []
    for fp in sorted(glob.glob(str(Path(reports_dir) / "*.jsonl"))):
        if Path(fp).name in exclude:
            continue
        for line in Path(fp).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(rec, dict):
                continue
            if rec.get("subject_id") and rec.get("object_id"):
                edges.append(rec)
            elif isinstance(rec.get("edges"), list):
                edges.extend(e for e in rec["edges"] if isinstance(e, dict))
                ents.extend(e for e in (rec.get("entities") or []) if isinstance(e, dict))
            elif rec.get("name"):
                ents.append(rec)
    return edges, ents


def load_entity_records(path) -> list[dict]:
    """Read a single entity-records JSONL (e.g. the harvest's ``combined.jsonl``, which
    :func:`load_edge_files` excludes) for ``registers`` synthesis. Returns [] if absent."""
    p = Path(path)
    if not p.exists():
        return []
    out: list[dict] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(rec, dict) and rec.get("name") and not rec.get("subject_id"):
            out.append(rec)
    return out


def build_graph(staged_edges, entity_records, clusters=None) -> list[dict]:
    """The full unified edge set: staged connector edges + synthesised registers + same_as."""
    return merge_edges(staged_edges, registers_edges(entity_records), same_as_edges(clusters or []))


def write_edges(edges, out_path) -> Path:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in edges) + ("\n" if edges else ""),
                   encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from-reports", default=str(_DEFAULT_DIR),
                    help="dir of staged connector *.jsonl edge/entity files (default reports/entity_kb)")
    ap.add_argument("--out", default="", help="output edges JSONL (default <from-reports>/edges.jsonl)")
    ap.add_argument("--entities", default="",
                    help="extra entity-records JSONL (e.g. the harvest's combined.jsonl) to feed "
                         "registers synthesis -- load_edge_files excludes combined.jsonl by default")
    args = ap.parse_args(argv)

    src_dir = Path(args.from_reports)
    out_path = Path(args.out) if args.out else src_dir / "edges.jsonl"
    staged_edges, ents = load_edge_files(src_dir)
    if args.entities:
        ents = ents + load_entity_records(args.entities)
    edges = build_graph(staged_edges, ents)
    write_edges(edges, out_path)
    man = build_manifest(edges)
    man_path = out_path.with_name("edges_manifest.json")
    man_path.write_text(json.dumps(man, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"unified {len(staged_edges)} staged + synthesised edges -> {man['n_edges']} edges "
          f"over {man['n_nodes']} nodes", file=sys.stderr)
    for pred, n in sorted(man["by_predicate"].items(), key=lambda kv: -kv[1]):
        print(f"  {pred:18} {n:>7}", file=sys.stderr)
    if man["unknown_predicates"]:
        print(f"  (unknown predicates: {man['unknown_predicates']})", file=sys.stderr)
    print(f"edges -> {out_path}\nmanifest -> {man_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
