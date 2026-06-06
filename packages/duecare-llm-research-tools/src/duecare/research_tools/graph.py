"""Deterministic auto-graph builder for the acquisition pipeline (the "graphed"
step). Links each doc/chunk to domain ENTITIES (ILO conventions, corridors,
statutes, frameworks) and links docs to each other by shared entities -- so
retrieval can surface "see also" neighbours and the corpus is navigable.

Offline, stdlib, regex/gazetteer-based (NO model -- GLiNER/spaCy were AMBER
model-download per the tooling survey). Deterministic: same docs + vocabulary
-> same graph. Scalable: co-mention edges use an inverted entity->docs index, so
it does not pay the O(n^2) all-pairs cost on a 10k corpus.
"""
from __future__ import annotations

import re

from pydantic import BaseModel


class Edge(BaseModel):
    source: str
    target: str
    relation: str   # "mentions" (doc->entity) | "co_mentions" (doc<->doc)
    weight: int = 1


# Seed gazetteer: entity_id -> regex patterns (case-insensitive). Curated, safe,
# extensible; the acquisition pipeline may pass a larger vocabulary.
DEFAULT_VOCABULARY: dict[str, list[str]] = {
    "ilo_c029": [r"\bc0?29\b", r"forced labour convention"],
    "ilo_c105": [r"\bc105\b", r"abolition of forced labour convention"],
    "ilo_c181": [r"\bc181\b", r"private employment agencies convention"],
    "ilo_c188": [r"\bc188\b", r"work in fishing convention"],
    "ilo_c189": [r"\bc189\b", r"domestic workers convention"],
    "ilo_c190": [r"\bc190\b", r"violence and harassment convention"],
    "palermo_protocol": [r"palermo protocol", r"trafficking in persons protocol"],
    "us_tvpa": [r"\btvpa\b", r"trafficking victims protection act"],
    "ph_ra8042": [r"\bra\s?8042\b", r"migrant workers and overseas filipinos act"],
    "ph_ra10022": [r"\bra\s?10022\b"],
    "uk_msa_2015": [r"modern slavery act 2015", r"\bmsa\b\s*s\.?\s*45"],
    "eu_dir_2011_36": [r"2011/36/eu", r"eu anti-trafficking directive"],
    "fatf": [r"\bfatf\b", r"financial action task force"],
    "kafala": [r"\bkafala\b", r"sponsorship system"],
    "non_punishment": [r"non-?punishment principle"],
}
_CORRIDOR = re.compile(r"\b([A-Z]{2})-([A-Z]{2})\b")


def extract_entities(text: str, vocabulary: dict[str, list[str]] | None = None) -> set[str]:
    """Deterministic gazetteer match -> set of entity ids found in ``text``.
    Corridors (e.g. PH-HK) are matched generically and emitted as
    ``corridor_XX-YY``."""
    vocab = vocabulary if vocabulary is not None else DEFAULT_VOCABULARY
    t = text or ""
    found: set[str] = set()
    for eid, pats in vocab.items():
        for p in pats:
            if re.search(p, t, re.I):
                found.add(eid)
                break
    for m in _CORRIDOR.finditer(t):  # corridor codes are already upper-case
        found.add(f"corridor_{m.group(1)}-{m.group(2)}")
    return found


def build_graph(
    docs: list,
    *,
    text_of,
    id_of,
    vocabulary: dict[str, list[str]] | None = None,
    min_shared: int = 2,
) -> dict:
    """Build ``{nodes, edges}``: doc->entity ``mentions`` edges plus doc<->doc
    ``co_mentions`` edges (weight = #shared entities) when two docs share at
    least ``min_shared`` entities. Deterministic (all outputs sorted). Pure --
    returns data, writes nothing."""
    doc_ents: dict[str, set[str]] = {}
    edges: list[Edge] = []
    for d in docs:
        did = id_of(d)
        ents = extract_entities(text_of(d), vocabulary)
        doc_ents[did] = ents
        for e in sorted(ents):
            edges.append(Edge(source=did, target=e, relation="mentions"))

    # inverted index entity -> docs; pair only docs that share an entity
    inv: dict[str, list[str]] = {}
    for did in sorted(doc_ents):
        for e in doc_ents[did]:
            inv.setdefault(e, []).append(did)
    pair_shared: dict[tuple[str, str], int] = {}
    for dlist in inv.values():
        ds = sorted(set(dlist))
        for i in range(len(ds)):
            for j in range(i + 1, len(ds)):
                pair_shared[(ds[i], ds[j])] = pair_shared.get((ds[i], ds[j]), 0) + 1
    for (a, b), cnt in sorted(pair_shared.items()):
        if cnt >= min_shared:
            edges.append(Edge(source=a, target=b, relation="co_mentions", weight=cnt))

    nodes = sorted(set(doc_ents) | {e for ents in doc_ents.values() for e in ents})
    return {"nodes": nodes, "edges": [e.model_dump() for e in edges]}
