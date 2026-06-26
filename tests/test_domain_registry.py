"""Tests for scripts/domain_registry.py -- the cross-domain benchmark registry loader."""
from __future__ import annotations

import importlib.util
import json
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


dr = _load("domain_registry", _ROOT / "scripts" / "domain_registry.py")


def test_registry_loads_and_has_expected_domains():
    doc = dr.load_registry()
    for d in ("trafficking", "money_laundering", "tax_evasion",
              "tariff_evasion", "market_manipulation"):
        assert d in doc["domains"], f"missing domain {d}"


def test_list_domains_is_sorted():
    ds = dr.list_domains()
    assert ds == sorted(ds)
    assert "trafficking" in ds and "money_laundering" in ds


def test_get_domain_has_required_shape():
    spec = dr.get_domain("money_laundering")
    for key in ("display_name", "scheme_pack", "rag_vertical", "rubric_anchors",
                "instruments", "regulators", "jurisdictions"):
        assert key in spec, f"missing top-level key {key}"
    for anchor in ("A_indicator", "B_law", "C_refuse", "D_resources", "E_safety"):
        assert anchor in spec["rubric_anchors"], f"missing rubric anchor {anchor}"
    for list_key in ("instruments", "regulators", "jurisdictions"):
        assert isinstance(spec[list_key], list) and spec[list_key]


def test_unknown_domain_raises_domain_error():
    with pytest.raises(dr.DomainError):
        dr.get_domain("nonexistent_domain")


def test_trafficking_scheme_pack_resolves_to_existing_file():
    p = dr.resolve_scheme_pack("trafficking")
    assert p.exists(), f"reference scheme pack should exist: {p}"


def test_money_laundering_seed_pack_exists_parses_and_spans_typologies():
    p = dr.resolve_scheme_pack("money_laundering")
    assert p.exists(), f"ML seed pack should exist: {p}"
    lines = [ln for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) >= 10, "expected a seed of >= 10 ML scheme prompts"
    categories = set()
    for line in lines:
        obj = json.loads(line)
        for key in ("id", "text", "category", "difficulty", "source"):
            assert key in obj, f"prompt {obj.get('id')!r} missing field {key}"
        categories.add(obj["category"])
    # the seed should span multiple AML typologies, not collapse to one
    assert len(categories) >= 5, f"expected >= 5 distinct ML typologies, got {sorted(categories)}"


def test_all_jsonl_seed_packs_parse_and_span_typologies():
    doc = dr.load_registry()
    jsonl_domains = [d for d, spec in doc["domains"].items()
                     if spec.get("scheme_pack_format") == "jsonl"]
    assert len(jsonl_domains) >= 4, f"expected >=4 jsonl seed domains, got {sorted(jsonl_domains)}"
    for d in jsonl_domains:
        p = dr.resolve_scheme_pack(d)
        assert p.exists(), f"{d} seed pack missing: {p}"
        lines = [ln for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
        assert len(lines) >= 10, f"{d}: expected >=10 prompts, got {len(lines)}"
        cats = set()
        for line in lines:
            obj = json.loads(line)
            for key in ("id", "text", "category", "difficulty", "source"):
                assert key in obj, f"{d} prompt {obj.get('id')!r} missing {key}"
            cats.add(obj["category"])
        assert len(cats) >= 4, f"{d}: expected >=4 typologies, got {sorted(cats)}"


def test_registry_records_propose_only_discipline():
    meta = json.dumps(dr.load_registry().get("_meta", {})).lower()
    assert "propose-only" in meta or "source-verif" in meta
