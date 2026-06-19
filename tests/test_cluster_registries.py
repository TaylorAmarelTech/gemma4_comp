"""Tests for scripts/cluster_registries.py -- the cross-registry clustering orchestrator.

Pure/offline: registry resolution is injected, so pooling (cap + source tag +
fault-isolation) and the summary report are tested without network or splink.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


cr = _load("cluster_registries", _ROOT / "scripts" / "cluster_registries.py")
el = _load("entity_link", _ROOT / "scripts" / "entity_link.py")


def test_resolve_pool_caps_tags_and_fault_isolates():
    def resolve(rid):
        if rid == "boom":
            raise RuntimeError("registry down")
        return [{"name": f"{rid}-{i}"} for i in range(10)]
    pool = cr.resolve_pool(["a", "boom", "b"], cap=3, resolve=resolve)
    assert len(pool) == 6                                   # a:3 + b:3, boom skipped (not fatal)
    assert {p["source"] for p in pool} == {"a", "b"}        # every record tagged with its source
    assert all("source" in p for p in pool)


def test_resolve_pool_no_cap_keeps_all():
    pool = cr.resolve_pool(["a"], cap=0, resolve=lambda rid: [{"name": str(i)} for i in range(7)])
    assert len(pool) == 7


def test_report_counts_dedup_and_cross_source():
    clusters = [{"n_sources": 2, "lei": "L1"}, {"n_sources": 1, "lei": ""},
                {"n_sources": 3, "lei": "L2"}]
    r = cr.report(clusters, n_pool=100, el=el)
    assert r["entities"] == 100 and r["clusters"] == 3
    assert r["dedup_removed"] == 97
    assert r["cross_source_clusters"] == 2 and r["lei_clusters"] == 2
    assert r["max_sources_in_a_cluster"] == 3
