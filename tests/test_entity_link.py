"""Tests for scripts/entity_link.py -- registry -> GLEIF LEI linkage.

The prepare/identifier helpers and the row->LEI assignment are pure and tested with a
synthetic splink predictions frame. One integration test runs a real (small) splink
``link_only`` model -- skipped if splink/pandas aren't installed.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


el = _load("entity_link", _ROOT / "scripts" / "entity_link.py")


# ---- pure helpers ---------------------------------------------------------

def test_extract_identifier_prefers_reg_number_then_strips_scheme():
    assert el.extract_identifier({"registered_as": "206-3384/560"}) == "2063384560"   # gleif side
    assert el.extract_identifier({"company_no": "10246724"}) == "10246724"            # registry side
    assert el.extract_identifier({"license_no": "GB-COH:2063384560"}) == "2063384560"  # scheme stripped
    assert el.extract_identifier({"name": "no id"}) == ""


def test_first_token_skips_generic_legal_words():
    assert el._first_token("the sunrise overseas manpower ltd") == "sunrise"
    assert el._first_token("ltd inc co") == "ltd"          # all-generic -> first token


def test_to_rows_shapes_for_splink():
    rows = el.to_rows([{"name": "Sunrise Overseas Manpower Inc", "jurisdiction": "ph",
                        "company_no": "R100"}], "registry")
    assert rows[0]["unique_id"] == "registry-0"
    assert rows[0]["name"] == "sunrise overseas manpower inc"
    assert rows[0]["name_first_token"] == "sunrise"
    assert rows[0]["jurisdiction"] == "PH" and rows[0]["identifier"] == "R100"


def test_best_lei_matches_picks_best_per_registry_and_thresholds():
    pd = pytest.importorskip("pandas")
    preds = pd.DataFrame([
        {"unique_id_l": "gleif-0", "unique_id_r": "registry-0", "match_probability": 0.97},
        {"unique_id_l": "gleif-1", "unique_id_r": "registry-0", "match_probability": 0.91},  # lower dup
        {"unique_id_l": "registry-1", "unique_id_r": "gleif-0", "match_probability": 0.60},  # < thr, reversed
    ])
    g_by = {"gleif-0": {"name": "Alpha Ltd", "lei": "LEI0", "registered_as": "R1"},
            "gleif-1": {"name": "Alpha Limited", "lei": "LEI1", "registered_as": "R1"}}
    r_by = {"registry-0": {"name": "Alpha", "company_no": "R1"},
            "registry-1": {"name": "Beta", "company_no": "R9"}}
    links = el.best_lei_matches(preds, g_by, r_by, threshold=0.9)
    assert len(links) == 1                              # registry-1 dropped (0.60 < 0.9)
    assert links[0]["lei"] == "LEI0"                    # best of the two candidates (0.97)
    assert links[0]["registry_name"] == "Alpha" and links[0]["via"] == "identifier"  # R1 == R1


def test_summarize_counts_link_rate_and_identifier_hits():
    s = el.summarize([{"via": "identifier"}, {"via": "name"}], n_registry=4)
    assert s == {"registry": 4, "linked": 2, "link_rate": 0.5, "via_identifier": 1}


# ---- splink integration (real model on a small set) -----------------------

def test_link_to_gleif_links_matching_companies():
    pytest.importorskip("splink")
    pytest.importorskip("pandas")
    # five clear matches (shared registered_as/company_no + near-identical name) + noise
    gleif = [{"name": f"Acme Trading {i} Limited", "lei": f"LEI{i}", "jurisdiction": "AE",
              "registered_as": f"R{i}"} for i in range(5)]
    gleif += [{"name": f"Unrelated Holding {i}", "lei": f"LX{i}", "jurisdiction": "AE",
               "registered_as": f"Z{i}"} for i in range(5)]
    registry = [{"name": f"ACME TRADING {i} INC", "jurisdiction": "AE", "company_no": f"R{i}",
                 "source": "test-reg"} for i in range(5)]
    registry += [{"name": f"Brandnew Co {i}", "jurisdiction": "AE", "company_no": f"Q{i}",
                  "source": "test-reg"} for i in range(5)]
    links = el.link_to_gleif(gleif, registry, threshold=0.5, max_pairs=1000)
    assert isinstance(links, list)
    by_name = {d["registry_name"]: d["lei"] for d in links}
    # the shared-identifier ACME rows must link to their LEI; the Brandnew rows must not
    assert by_name.get("ACME TRADING 0 INC") == "LEI0"
    assert not any(d["registry_name"].startswith("Brandnew") for d in links)


# ---- clustering -----------------------------------------------------------

def test_assemble_clusters_groups_and_flags_cross_source():
    pd = pytest.importorskip("pandas")
    records = [{"name": "Huawei Technologies", "source": "dod", "lei": ""},
               {"name": "Huawei Technologies Co", "source": "special", "lei": "L9"},
               {"name": "Unique Co", "source": "afdb", "lei": ""}]
    cdf = pd.DataFrame([{"unique_id": "e-0", "cluster_id": "c1"},
                        {"unique_id": "e-1", "cluster_id": "c1"},
                        {"unique_id": "e-2", "cluster_id": "c2"}])
    clusters = el.assemble_clusters(cdf, records)
    assert clusters[0]["n_sources"] == 2 and clusters[0]["sources"] == ["dod", "special"]
    assert clusters[0]["lei"] == "L9" and clusters[0]["size"] == 2     # LEI propagated in-cluster
    cross = el.cross_source_clusters(clusters)
    assert len(cross) == 1 and cross[0]["cluster_id"] == "c1"


def test_cluster_entities_collapses_cross_source_duplicates():
    pytest.importorskip("rapidfuzz")
    names = ["Globex Manufacturing", "Initech Solutions", "Umbrella Logistics",
             "Soylent Foods", "Hooli Robotics"]                        # distinct, not index-suffixed
    recs = [{"name": f"{n} Ltd", "jurisdiction": "PH", "company_no": f"CN10{i:02d}", "source": "a"}
            for i, n in enumerate(names)]
    recs += [{"name": f"{n.upper()} INC", "jurisdiction": "PH", "company_no": f"CN10{i:02d}", "source": "b"}
             for i, n in enumerate(names)]                             # same company_no, other source
    recs += [{"name": f"Zeta {n} Holdings", "jurisdiction": "PH", "company_no": f"DX20{i:02d}", "source": "a"}
             for i, n in enumerate(names)]                             # unrelated singletons
    clusters = el.cluster_entities(recs, threshold=0.8)
    cross = el.cross_source_clusters(clusters)
    assert len(cross) >= 4 and all(c["n_sources"] == 2 for c in cross)  # each name's a~b pair merged
