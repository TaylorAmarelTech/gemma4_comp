"""Tests for the per-prompt dimension relevance selector."""
from __future__ import annotations

import importlib
import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SCRIPTS = _ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

ds = importlib.import_module("dimension_selector")

_DIMS = [
    {"id": "response_quality.a", "group": "response_quality"},
    {"id": "ilo_indicator.deception", "group": "ilo_indicator"},
    {"id": "scheme_detection.x", "group": "scheme_detection"},
    {"id": "sector_awareness.domestic_work", "group": "sector_awareness"},
    {"id": "sector_awareness.fishing", "group": "sector_awareness"},
    {"id": "corridor_awareness.PH_HK", "group": "corridor_awareness"},
    {"id": "corridor_awareness.NP_GULF", "group": "corridor_awareness"},
    {"id": "pretext_resistance.a", "group": "pretext_resistance"},
    {"id": "financial_obfuscation_detection.a", "group": "financial_obfuscation_detection"},
    {"id": "benevolent_framing_resistance.a", "group": "benevolent_framing_resistance"},
]


def test_worker_prompt_selects_matching_sector_only_and_no_attack_groups():
    meta = {"category": "sector_scenario", "framing": "worker_query",
            "sector": "domestic_work", "corridor": "PH_HK"}
    ids = set(ds.relevant_dim_ids(meta, _DIMS))
    assert "response_quality.a" in ids and "ilo_indicator.deception" in ids
    assert "sector_awareness.domestic_work" in ids          # matching sector
    assert "sector_awareness.fishing" not in ids            # other sector excluded
    assert "corridor_awareness.PH_HK" in ids
    assert "corridor_awareness.NP_GULF" not in ids
    assert "pretext_resistance.a" not in ids                # not an attack prompt


def test_pretext_jailbreak_selects_attack_groups_not_sector():
    meta = {"category": "pretext_jailbreak", "framing": "legitimizing_pretext"}
    ids = set(ds.relevant_dim_ids(meta, _DIMS))
    assert "pretext_resistance.a" in ids
    assert "scheme_detection.x" in ids                      # attack still implies scheme
    assert "sector_awareness.domestic_work" not in ids      # no sector tagged
    assert "corridor_awareness.PH_HK" not in ids


def test_financial_and_benevolent_triggers():
    assert "financial_obfuscation_detection.a" in set(ds.relevant_dim_ids(
        {"category": "money_mule", "framing": "mixed"}, _DIMS))
    assert "benevolent_framing_resistance.a" in set(ds.relevant_dim_ids(
        {"category": "benevolent_framing", "framing": "benevolent"}, _DIMS))


def test_selection_is_a_strict_subset():
    meta = {"category": "sector_scenario", "sector": "domestic_work"}
    ids = ds.relevant_dim_ids(meta, _DIMS)
    allids = {d["id"] for d in _DIMS}
    assert set(ids) <= allids and len(ids) < len(_DIMS)     # fewer than all
