"""Tests for scripts/entity_edges.py -- unify connector edges into one graph file.

Pure/offline. Fixtures mirror the real edge shapes the connectors emit (gleif_rr parent_of,
openownership_bods owns_or_controls, domain_intel nested edges, entity_link clusters) plus
synthesised registry `registers` edges. All names are synthetic.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


ee = _load("entity_edges", _ROOT / "scripts" / "entity_edges.py")

PARENT = {"subject_id": "LEI-PARENT", "predicate": "parent_of", "object_id": "LEI-CHILD",
          "source": "GLEIF Level-2 RR (CC0)", "weight": 0.9, "qualifier": {"rel_type": "ultimate"}}
OWNS = {"subject_id": "person-1", "predicate": "owns_or_controls", "object_id": "LEI-CHILD",
        "source": "OpenOwnership BODS", "weight": 0.75, "qualifier": {"share": 60}}


def test_normalize_edge_coerces_and_validates():
    e = ee.normalize_edge({"subject_id": " A ", "predicate": "parent_of", "object_id": "B",
                           "weight": "1.5"})
    assert e["subject_id"] == "A" and e["object_id"] == "B"
    assert e["weight"] == 1.0                       # clamped to [0,1]
    assert e["qualifier"] == {} and e["source"] == ""
    # missing endpoints / bad input -> None
    assert ee.normalize_edge({"subject_id": "A", "predicate": "x"}) is None
    assert ee.normalize_edge({"subject_id": "", "predicate": "p", "object_id": "o"}) is None
    assert ee.normalize_edge("nope") is None


def test_normalize_edge_bad_weight_falls_back():
    e = ee.normalize_edge({"subject_id": "A", "predicate": "p", "object_id": "B", "weight": "abc"})
    assert e["weight"] == 0.5                        # default when unparseable


def test_merge_dedups_same_triple_keeps_max_weight_and_unions_sources():
    low = {**PARENT, "weight": 0.4, "source": "src-A"}
    high = {**PARENT, "weight": 0.9, "source": "src-B"}
    merged = ee.merge_edges([low, high])
    assert len(merged) == 1
    assert merged[0]["weight"] == 0.9
    assert merged[0]["source"] == "src-A | src-B"   # sources unioned, sorted


def test_merge_keeps_distinct_qualifiers_and_sorts():
    direct = {**PARENT, "qualifier": {"rel_type": "direct"}}
    ultimate = {**PARENT, "qualifier": {"rel_type": "ultimate"}}
    merged = ee.merge_edges([direct, ultimate, OWNS])
    assert len(merged) == 3                          # distinct qualifiers both survive
    preds = [e["predicate"] for e in merged]
    assert preds == sorted(preds)                    # stable predicate-first sort


def test_merge_is_idempotent_over_overlapping_inputs():
    once = ee.merge_edges([PARENT, OWNS])
    twice = ee.merge_edges([PARENT, OWNS], [PARENT, OWNS])
    assert once == twice


def test_registers_edges_from_entity_records():
    recs = [{"name": "Sailwind Trading FZE", "lei": "254900N2EEPSHPNU0H50",
             "entity_type": "company", "jurisdiction": "AE", "status": "ISSUED",
             "source": "GLEIF LEI (api.gleif.org, CC0)"},
            {"name": "Sunrise Overseas Recruitment", "entity_type": "recruitment_agency",
             "jurisdiction": "PH", "source": "PH DMW"},
            {"name": "No Source Co"},                # skipped: no source
            {"source": "X only"}]                    # skipped: no name
    edges = ee.registers_edges(recs)
    assert len(edges) == 2
    by_obj = {e["object_id"]: e for e in edges}
    # LEI-keyed object id when present (joins the parent_of edges); name otherwise
    assert "254900N2EEPSHPNU0H50" in by_obj and "Sunrise Overseas Recruitment" in by_obj
    e = by_obj["254900N2EEPSHPNU0H50"]
    assert e["predicate"] == "registers" and e["subject_id"] == "GLEIF LEI (api.gleif.org, CC0)"
    assert e["qualifier"]["kind"] == "registry_listing" and e["qualifier"]["jurisdiction"] == "AE"


def test_same_as_edges_from_clusters():
    clusters = [{"cluster_id": "c1", "size": 3, "n_sources": 2, "lei": "LEI-X",
                 "names": ["Goldfield Mariners Inc", "Goldfield Mariners"]},
                {"cluster_id": "c2", "size": 1, "n_sources": 1, "lei": "",
                 "names": ["Solo Corp"]}]            # single id -> no edge
    edges = ee.same_as_edges(clusters)
    assert len(edges) == 2                            # canonical LEI-X -> each of 2 names
    assert all(e["predicate"] == "same_as" and e["subject_id"] == "LEI-X" for e in edges)
    assert {e["object_id"] for e in edges} == {"Goldfield Mariners Inc", "Goldfield Mariners"}


def test_node_set_and_manifest_flag_unknown_predicates():
    edges = ee.merge_edges([PARENT, OWNS, {"subject_id": "a", "predicate": "weird_rel",
                                           "object_id": "b"}])
    assert ee.node_set(edges) == sorted({"LEI-PARENT", "LEI-CHILD", "person-1", "a", "b"})
    man = ee.build_manifest(edges)
    assert man["n_edges"] == 3 and man["n_nodes"] == 5
    assert man["by_predicate"]["parent_of"] == 1
    assert man["unknown_predicates"] == ["weird_rel"]


def test_load_edge_files_handles_all_three_line_shapes(tmp_path):
    # flat edge file (gleif_rr / bods shape)
    (tmp_path / "gleif_rr_ae.jsonl").write_text(json.dumps(PARENT) + "\n", encoding="utf-8")
    # nested domain_intel shape: one record with edges[] + entities[]
    (tmp_path / "domains.jsonl").write_text(json.dumps({
        "domain": "example-recruit.test",
        "entities": [{"name": "Example Recruit Ltd", "entity_type": "organization"}],
        "edges": [{"subject_id": "Example Recruit Ltd", "predicate": "registers",
                   "object_id": "example-recruit.test", "source": "rdap", "weight": 0.8}],
    }) + "\nnot-json\n", encoding="utf-8")                       # bad line skipped
    # plain entity record file
    (tmp_path / "agencies.jsonl").write_text(json.dumps({
        "name": "Sunrise Overseas Recruitment", "entity_type": "recruitment_agency",
        "source": "PH DMW"}) + "\n", encoding="utf-8")
    # excluded files must be ignored
    (tmp_path / "combined.jsonl").write_text(json.dumps({"name": "X", "source": "Y"}) + "\n",
                                             encoding="utf-8")

    edges, ents = ee.load_edge_files(tmp_path)
    assert len(edges) == 2                                       # 1 flat + 1 nested
    assert {e["predicate"] for e in edges} == {"parent_of", "registers"}
    names = {e["name"] for e in ents}
    assert names == {"Example Recruit Ltd", "Sunrise Overseas Recruitment"}  # combined.jsonl excluded


def test_load_entity_records_reads_combined_style_file(tmp_path):
    f = tmp_path / "combined.jsonl"
    f.write_text("\n".join([
        json.dumps({"name": "Acme Manning Ltd", "entity_type": "company", "source": "X reg"}),
        "",                                                       # blank line skipped
        json.dumps({"subject_id": "a", "predicate": "p", "object_id": "b"}),  # an edge, not entity
        json.dumps({"entity_type": "company", "source": "no name"}),          # no name, skipped
    ]) + "\n", encoding="utf-8")
    recs = ee.load_entity_records(f)
    assert [r["name"] for r in recs] == ["Acme Manning Ltd"]      # only the named entity record
    assert ee.load_entity_records(tmp_path / "missing.jsonl") == []


def test_build_graph_end_to_end_and_write(tmp_path):
    staged = [PARENT, OWNS]
    ents = [{"name": "Sunrise Overseas Recruitment", "entity_type": "recruitment_agency",
             "source": "PH DMW"}]
    clusters = [{"cluster_id": "c1", "n_sources": 2, "lei": "LEI-X",
                 "names": ["Alpha Co", "Alpha Company"]}]
    edges = ee.build_graph(staged, ents, clusters)
    preds = {e["predicate"] for e in edges}
    assert preds == {"parent_of", "owns_or_controls", "registers", "same_as"}
    out = ee.write_edges(edges, tmp_path / "edges.jsonl")
    lines = [json.loads(ln) for ln in out.read_text(encoding="utf-8").splitlines()]
    assert len(lines) == len(edges) and all("subject_id" in ln for ln in lines)
