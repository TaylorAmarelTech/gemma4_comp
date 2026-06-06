"""Tests for the deterministic auto-graph builder (acquisition pipeline)."""
from __future__ import annotations

from duecare.research_tools.graph import build_graph, extract_entities

# Synthetic public-law-style docs (no real PII). D1 and D2 share C189 + a
# corridor; D3 is an unrelated framework doc.
D1 = {"id": "d1", "t": "Under C189 the domestic worker on the PH-HK corridor keeps her passport."}
D2 = {"id": "d2", "t": "The domestic workers convention (C189) applies; on PH-HK fees are unlawful."}
D3 = {"id": "d3", "t": "FATF guidance on financial flows and the financial action task force typologies."}


def test_extract_entities_finds_conventions():
    ents = extract_entities("This invokes C189 and the Palermo Protocol.")
    assert "ilo_c189" in ents and "palermo_protocol" in ents


def test_extract_entities_finds_corridor():
    assert "corridor_PH-HK" in extract_entities("deployed on the PH-HK corridor")


def test_extract_entities_empty():
    assert extract_entities("") == set()
    assert extract_entities("a paragraph about nothing in particular") == set()


def test_mentions_edges_emitted():
    g = build_graph([D1], text_of=lambda d: d["t"], id_of=lambda d: d["id"])
    mentions = {(e["source"], e["target"]) for e in g["edges"] if e["relation"] == "mentions"}
    assert ("d1", "ilo_c189") in mentions
    assert ("d1", "corridor_PH-HK") in mentions


def test_co_mention_edge_when_sharing_enough():
    g = build_graph([D1, D2, D3], text_of=lambda d: d["t"], id_of=lambda d: d["id"], min_shared=2)
    co = {(e["source"], e["target"]): e["weight"] for e in g["edges"] if e["relation"] == "co_mentions"}
    assert ("d1", "d2") in co            # share C189 + corridor_PH-HK
    assert co[("d1", "d2")] >= 2
    assert ("d1", "d3") not in co and ("d2", "d3") not in co  # D3 shares nothing


def test_min_shared_threshold_respected():
    g = build_graph([D1, D2], text_of=lambda d: d["t"], id_of=lambda d: d["id"], min_shared=3)
    co = [e for e in g["edges"] if e["relation"] == "co_mentions"]
    assert co == []  # they share exactly 2 entities, threshold is 3


def test_deterministic_and_nodes_listed():
    kw = dict(text_of=lambda d: d["t"], id_of=lambda d: d["id"])
    a = build_graph([D1, D2, D3], **kw)
    b = build_graph([D1, D2, D3], **kw)
    assert a == b
    assert "d1" in a["nodes"] and "ilo_c189" in a["nodes"] and "fatf" in a["nodes"]
