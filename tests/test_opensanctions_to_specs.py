"""Tests for scripts/opensanctions_to_specs.py -- draft-spec scaffolder.

Pure/offline: harvest records in, draft registry_specs blocks out. The drafts are
deliberately NOT runnable (fields = TODO); these tests pin that contract.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

pytest.importorskip("yaml")

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


ots = _load("opensanctions_to_specs", _ROOT / "scripts" / "opensanctions_to_specs.py")


def _rec(**over):
    base = {"name": "Brazil CEIS Disreputable Companies", "country": "BR", "category": "registry",
            "entity_type": "company", "publisher": "CGU", "data_url": "https://x/ceis.csv",
            "data_format": "csv"}
    base.update(over)
    return base


def test_map_format_known_and_unknown():
    assert ots.map_format("JSON") == "json"
    assert ots.map_format("CSV") == "csv"
    assert ots.map_format("HTML") == "html_table"
    assert ots.map_format("XML") is None          # unsupported => skip


def test_draft_spec_id_shape():
    assert ots.draft_spec_id(_rec()) == "os_br_brazil_ceis_disreputable_com"


def test_to_draft_spec_marks_unverified_with_todo_fields():
    spec = ots.to_draft_spec(_rec(data_format="JSON", data_url="https://x/a.json"))
    assert spec["format"] == "json" and spec["jurisdiction"] == "BR"
    assert spec["_needs_verification"] is True
    assert "TODO" in spec["fields"]["name"]       # never a fabricated field map


def test_to_draft_spec_skips_no_endpoint_or_unsupported_format():
    assert ots.to_draft_spec(_rec(data_url="")) is None
    assert ots.to_draft_spec(_rec(data_format="XML")) is None


def test_drafts_dedups_skips_existing_and_filters_category():
    recs = [
        _rec(name="A Register", data_url="https://x/a.json", data_format="JSON"),
        _rec(name="A Register", data_url="https://x/a.json", data_format="JSON"),   # dup id
        _rec(name="Sanctions List", category="sanctions", data_url="https://x/s.json", data_format="JSON"),
    ]
    out = ots.drafts(recs, existing_ids=set(), categories={"registry"})
    assert len(out) == 1                            # deduped + sanctions filtered out

    already = {ots.draft_spec_id(_rec(name="A Register"))}
    assert ots.drafts(recs, existing_ids=already, categories={"registry"}) == []  # skipped as live


def test_summarize_counts():
    out = ots.drafts([_rec(data_url="https://x/a.json", data_format="JSON"),
                      _rec(name="B Register", data_url="https://x/b.csv", data_format="CSV")],
                     existing_ids=set())
    s = ots.summarize(out)
    assert s["drafts"] == 2 and s["by_format"] == {"json": 1, "csv": 1}


def test_emit_yaml_labels_drafts_not_runnable():
    import yaml
    text = ots._emit_yaml(ots.drafts([_rec(data_url="https://x/a.json", data_format="JSON")],
                                      existing_ids=set()))
    parsed = yaml.safe_load(text)
    assert parsed["catalog"] == "opensanctions_draft_specs"
    assert "NOT runnable" in parsed["purpose"]
