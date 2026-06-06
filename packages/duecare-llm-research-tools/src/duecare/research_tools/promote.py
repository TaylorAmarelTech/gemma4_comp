"""Promote staged acquisition chunks into an importable knowledge bundle.

The acquisition pipeline stages chunks (propose-only). This module turns those
staged chunks + the doc graph into knowledge ENVELOPES in the exact shape the
existing ``/api/knowledge/import`` flow accepts -- so promoted docs round-trip
through the designed, tested ingestion path (no harness change, no corpus-file
bloat) and show up on the Knowledge / Status surfaces.

Envelope shape (matches scripts/build_static_samples.py):
    {schema_version, knowledge_object_type, id, version, provenance, content, tags}
The bundle ZIP entries are pathed ``<type>/<id>.json`` with the envelope id equal
to the filename stem (the importer requires this).

Pure + deterministic: ``created_at`` is injected (no clock here), so the same
staged input yields byte-identical envelopes. Writes nothing -- the runner
persists the bundle.
"""
from __future__ import annotations

import json
import re

from .relevance import TIER_RANK, relevance

_ID_SAFE = re.compile(r"[^a-z0-9]+")
_VERIFY_NOTE = ("Acquired automatically from a public source by the DueCare "
                "acquisition pipeline. Review and verify against the cited source "
                "before production use; volatile facts (numbers, contacts) should "
                "come from tools, not memorized.")


def sanitize_id(s: str) -> str:
    """Filename-safe stable id: lowercase, non-alnum runs -> single hyphen."""
    return _ID_SAFE.sub("-", (s or "").lower()).strip("-") or "x"


def chunk_envelope_id(chunk: dict) -> str:
    """Stable envelope id for a staged chunk (``acq-<doc>-c<ordinal>``)."""
    doc = sanitize_id(str(chunk.get("doc_id", "")))
    return f"acq-{doc}-c{int(chunk.get('ordinal', 0)):03d}"


def chunk_to_rag_doc(chunk: dict, *, created_at: str, rel: dict | None = None) -> dict:
    """One staged chunk -> a ``rag_doc`` knowledge envelope. ``rel`` (relevance
    score dict) is recorded in provenance + a ``relevance-<tier>`` tag."""
    base = chunk.get("title") or chunk.get("doc_id") or "Acquired document"
    title = f"{base} (part {int(chunk.get('ordinal', 0)) + 1})"
    jur = (chunk.get("jurisdictions") or [None])[0]
    tags = ["acquired"]
    if rel:
        tags.append(f"relevance-{rel['tier']}")
    if chunk.get("source_tier"):
        tags.append(sanitize_id(chunk["source_tier"]))
    tags.extend(sanitize_id(s) for s in (chunk.get("signals") or [])[:4])
    return {
        "schema_version": "1.0",
        "knowledge_object_type": "rag_doc",
        "id": chunk_envelope_id(chunk),
        "version": "v1",
        "provenance": {
            "kind": "acquired_public_source",
            "created_by": "scripts/promote_acquisition.py",
            "created_at": created_at,
            "source_url": chunk.get("url"),
            "relevance": rel or {},
            "notes": "Automated acquisition; review before production use.",
        },
        "content": {
            "title": title,
            "citation": chunk.get("url") or "",
            "jurisdiction": jur,
            "text": chunk.get("text", ""),
            "source_url": chunk.get("url"),
            "verification_note": _VERIFY_NOTE,
        },
        "tags": tags,
    }


def citation_edges(graph: dict, doc_to_env_id: dict[str, str], *, created_at: str) -> list[dict]:
    """``co_mentions`` graph edges -> ``citation_edge`` envelopes between the
    representative (first) chunk envelope of each linked doc."""
    out: list[dict] = []
    for e in graph.get("edges", []):
        if e.get("relation") != "co_mentions":
            continue
        a, b = doc_to_env_id.get(e.get("source")), doc_to_env_id.get(e.get("target"))
        if not a or not b:
            continue
        out.append({
            "schema_version": "1.0",
            "knowledge_object_type": "citation_edge",
            "id": f"acqedge-{sanitize_id(a)}--{sanitize_id(b)}",
            "version": "v1",
            "provenance": {
                "kind": "acquired_public_source",
                "created_by": "scripts/promote_acquisition.py",
                "created_at": created_at,
                "notes": "Doc co-mention edge from the acquisition graph.",
            },
            "content": {
                "from_doc_id": a, "to_doc_id": b,
                "relation": "co_mentions", "weight": int(e.get("weight", 1)),
            },
            "tags": ["acquired", "graph_edge"],
        })
    return out


def cap_per_doc(staged_chunks: list[dict], max_per_doc: int | None) -> list[dict]:
    """Keep at most ``max_per_doc`` chunks per doc (the lowest-ordinal ones, i.e.
    the substantive head), so one sprawling source page can't flood the corpus.
    ``None`` keeps everything. Deterministic; preserves input order."""
    if not max_per_doc or max_per_doc <= 0:
        return list(staged_chunks)
    return [c for c in staged_chunks if int(c.get("ordinal", 0)) < max_per_doc]


def build_envelopes(
    staged_chunks: list[dict], graph: dict, *, created_at: str,
    max_per_doc: int | None = None, min_tier: str = "medium",
) -> list[dict]:
    """All envelopes for a staged batch: a ``rag_doc`` per chunk that passes the
    trafficking-relevance gate (``min_tier``) + ``citation_edge`` per doc
    co-mention. ``max_per_doc`` caps chunks per source (corpus balance). The gate
    keeps broad harvested gov pages from diluting the corpus. Deterministic."""
    staged_chunks = cap_per_doc(staged_chunks, max_per_doc)
    floor = TIER_RANK.get(min_tier, 1)
    rag: list[dict] = []
    kept: list[dict] = []
    for c in staged_chunks:
        rel = relevance(c.get("text", ""), signals=c.get("signals"))
        if TIER_RANK[rel["tier"]] < floor:
            continue  # off-topic / below the relevance floor -> not promoted
        rag.append(chunk_to_rag_doc(c, created_at=created_at, rel=rel))
        kept.append(c)
    # first chunk (ordinal 0) of each KEPT doc is its representative for edges
    doc_to_env: dict[str, str] = {}
    for c in kept:
        if int(c.get("ordinal", 0)) == 0:
            doc_to_env[str(c.get("doc_id"))] = chunk_envelope_id(c)
    edges = citation_edges(graph, doc_to_env, created_at=created_at)
    return rag + edges


def bundle_entries(envelopes: list[dict]) -> list[tuple[str, bytes]]:
    """``(zip_path, bytes)`` per envelope, pathed ``<type>/<id>.json`` as the
    importer requires. Sorted for deterministic archives."""
    entries: list[tuple[str, bytes]] = []
    for env in envelopes:
        path = f"{env['knowledge_object_type']}/{env['id']}.json"
        entries.append((path, json.dumps(env, indent=2, ensure_ascii=False).encode("utf-8")))
    return sorted(entries, key=lambda t: t[0])
