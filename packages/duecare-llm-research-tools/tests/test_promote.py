"""Tests for promoting staged chunks into importable knowledge envelopes."""
from __future__ import annotations

import json

from duecare.research_tools.promote import (
    build_envelopes, bundle_entries, cap_per_doc, chunk_envelope_id, chunk_to_rag_doc, sanitize_id,
)

TS = "2026-06-06T00:00:00Z"

# Two staged docs (each one chunk, ordinal 0) that co-mention in the graph.
# Real prose so they clear both the relevance and meaningfulness gates.
C1 = {"doc_id": "SRC-CAND-AA#x", "ordinal": 0, "title": "DW rights",
      "text": ("Under ILO C189 the domestic worker on the PH-HK corridor keeps custody of her "
               "passport at all times during employment, and the employer bears the full cost of "
               "recruitment and deployment so that no recruitment fee is charged to the worker."),
      "url": "https://example.org/a", "source_tier": "official_government",
      "jurisdictions": ["Philippines"], "signals": ["debt_bondage", "forced_labor"]}
C2 = {"doc_id": "SRC-CAND-BB", "ordinal": 0, "title": "Fees rule",
      "text": ("On the PH-HK corridor recruitment fees charged to the worker are unlawful under "
               "ILO C189, and any amount collected must be refunded in full because charging the "
               "worker creates a debt that can be used to coerce continued labour."),
      "url": "https://example.org/b"}
GRAPH = {"nodes": ["SRC-CAND-AA#x", "SRC-CAND-BB"],
         "edges": [{"source": "SRC-CAND-AA#x", "target": "SRC-CAND-BB",
                    "relation": "co_mentions", "weight": 2}]}


def test_sanitize_id_is_filename_safe():
    assert sanitize_id("SRC-CAND-AA#x") == "src-cand-aa-x"
    assert "#" not in chunk_envelope_id(C1) and "/" not in chunk_envelope_id(C1)


def test_chunk_to_rag_doc_shape():
    env = chunk_to_rag_doc(C1, created_at=TS)
    assert env["knowledge_object_type"] == "rag_doc"
    assert env["id"] == chunk_envelope_id(C1)
    assert env["content"]["text"] == C1["text"]
    assert env["content"]["citation"] == C1["url"]
    assert env["provenance"]["created_at"] == TS
    assert "acquired" in env["tags"] and "official-government" in env["tags"]


def test_build_envelopes_counts_and_edge():
    envs = build_envelopes([C1, C2], GRAPH, created_at=TS)
    rag = [e for e in envs if e["knowledge_object_type"] == "rag_doc"]
    edges = [e for e in envs if e["knowledge_object_type"] == "citation_edge"]
    assert len(rag) == 2
    assert len(edges) == 1
    assert edges[0]["content"]["from_doc_id"] == chunk_envelope_id(C1)
    assert edges[0]["content"]["to_doc_id"] == chunk_envelope_id(C2)
    assert edges[0]["content"]["weight"] == 2


def test_bundle_entries_paths_match_importer_contract():
    envs = build_envelopes([C1, C2], GRAPH, created_at=TS)
    entries = bundle_entries(envs)
    for path, raw in entries:
        env = json.loads(raw)
        # importer requires <type>/<id>.json with stem == id
        assert path == f"{env['knowledge_object_type']}/{env['id']}.json"
    assert entries == sorted(entries, key=lambda t: t[0])  # deterministic order


def test_deterministic():
    a = build_envelopes([C1, C2], GRAPH, created_at=TS)
    b = build_envelopes([C1, C2], GRAPH, created_at=TS)
    assert a == b


def test_cap_per_doc_trims_sprawling_source():
    big = [{"doc_id": "D", "ordinal": i, "text": f"t{i}", "url": "u"} for i in range(10)]
    capped = cap_per_doc(big, 3)
    assert [c["ordinal"] for c in capped] == [0, 1, 2]   # keeps the head
    assert cap_per_doc(big, None) == big                  # None keeps all
    # build_envelopes honors the cap ('low' floors isolate the cap from the gates)
    envs = build_envelopes(big, {"edges": []}, created_at=TS, max_per_doc=3,
                           min_tier="low", min_meaning="low")
    assert len([e for e in envs if e["knowledge_object_type"] == "rag_doc"]) == 3


def test_relevance_gate_excludes_offtopic():
    on = {"doc_id": "d1", "ordinal": 0, "url": "u",
          "text": "ILO C189 domestic worker recruitment fees and passport retention; debt bondage."}
    off = {"doc_id": "d2", "ordinal": 0, "url": "u2",
           "text": "Carbon border adjustment certificates for embedded emissions under the trading scheme."}
    envs = build_envelopes([on, off], {"edges": []}, created_at=TS,
                           min_tier="medium", min_meaning="low")
    rag = [e for e in envs if e["knowledge_object_type"] == "rag_doc"]
    assert len(rag) == 1                                   # off-topic chunk gated out
    assert rag[0]["id"] == chunk_envelope_id(on)
    assert any(t.startswith("relevance-") for t in rag[0]["tags"])
    assert rag[0]["provenance"]["relevance"]["tier"] in ("medium", "high")


def test_domain_sense_collision_is_promoted_but_flagged_for_review():
    # on-topic enough to pass the relevance gate ("freedom of movement", "exit permit"
    # hit the restricted_movement family) BUT the ambiguous word "bond" resolves to
    # finance -- a cross-domain false positive that must be routed to manual review,
    # not silently staged.
    collide = {"doc_id": "dC", "ordinal": 0, "url": "u",
               "text": ("Freedom of movement of capital is essential to the bond market. "
                        "Investors weigh the issuer's coupon and yield before they buy. "
                        "The exit permit for funds is a purely financial concept here.")}
    envs = build_envelopes([collide], {"edges": []}, created_at=TS,
                           min_tier="medium", min_meaning="low")
    rag = [e for e in envs if e["knowledge_object_type"] == "rag_doc"]
    assert len(rag) == 1                                   # promoted (not dropped)
    tags = rag[0]["tags"]
    assert "needs-review" in tags and "sense-collision" in tags
    assert "offdomain-finance" in tags
    assert rag[0]["provenance"]["domain_sense"]["collision"] is True


def test_clean_chunk_is_not_flagged_for_sense_review():
    envs = build_envelopes([C1, C2], GRAPH, created_at=TS)
    rag = [e for e in envs if e["knowledge_object_type"] == "rag_doc"]
    for e in rag:
        assert "needs-review" not in e["tags"] and "sense-collision" not in e["tags"]
        assert e["provenance"]["domain_sense"]["collision"] is False


def test_meaningfulness_gate_excludes_boilerplate():
    # both are on-topic, but the second is a short nav fragment with no substance
    rich = {"doc_id": "d1", "ordinal": 0, "url": "u",
            "text": ("Recruitment fees charged to a migrant domestic worker are unlawful; the "
                     "employer bears the full cost of deployment and the worker keeps her passport, "
                     "so that no debt is created that could be used to coerce continued labour.")}
    boiler = {"doc_id": "d2", "ordinal": 0, "url": "u2",
              "text": "Recruitment fees. Migrant worker. Passport. Visa. Home. Contact."}
    envs = build_envelopes([rich, boiler], {"edges": []}, created_at=TS,
                           min_tier="medium", min_meaning="medium")
    rag = [e for e in envs if e["knowledge_object_type"] == "rag_doc"]
    assert len(rag) == 1 and rag[0]["id"] == chunk_envelope_id(rich)
    assert any(t.startswith("meaningful-") for t in rag[0]["tags"])
