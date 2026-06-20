"""Primitives-conformance suite -- enforce DueCare's standardized objects/contracts.

This is DATA-DRIVEN over the LIVE registries, so a new harness / model target / logic path
/ canonical-schema export is automatically held to its contract with no hand-written
per-instance test. It complements (does not duplicate) the existing suites:
``test_workbench_inventory_integrity`` already enforces spec *completeness* (every spec has
workflow / model_targets / privacy_boundaries / ...); this suite enforces the *shape* of
each primitive and the *consistency* between a harness module and its spec.

Catalog of the primitives this enforces: docs/contracts_catalog.md.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from collections.abc import Mapping
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]


def _load_script(name):
    spec = importlib.util.spec_from_file_location(name, _ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _field(obj, name, default=None):
    """Read a field whether the instance is a dataclass or a Mapping (specs allow both)."""
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


# the documented model-target transports (rule 81_canonical_runtime). Currently used:
# gemma4_runtime / duecare_model_adapter / frontier_api / none; the rest are the documented
# universal-harness targets reserved for future use. A NEW transport must be registered here
# -- that deliberate registration is exactly the standardization the contract enforces.
KNOWN_TRANSPORTS = frozenset({
    "gemma4_runtime", "duecare_model_adapter", "frontier_api", "none",
    "ollama", "openai_compatible", "anthropic", "gemini", "hf_endpoint", "callable",
})
KNOWN_MODEL_CALL = frozenset({"none", "optional", "required", "hybrid"})
KNOWN_TIERS = frozenset({"primary", "secondary"})


def _harnesses():
    from duecare.chat.harnesses import all_harnesses
    return all_harnesses()


# ---------------------------------------------------------------------------
# Primitive 1 -- the harness module contract
# ---------------------------------------------------------------------------

def test_every_harness_satisfies_the_module_primitive():
    for m in _harnesses():
        assert isinstance(m.name, str) and m.name, m
        assert isinstance(m.applied_layers, tuple), m.name
        assert isinstance(m.consumes, tuple) and isinstance(m.emits, tuple), m.name
        assert callable(m.register_routes), m.name
        assert m.spec is not None, m.name


def test_harness_module_and_spec_are_consistent():
    for m in _harnesses():
        s = m.spec
        assert s.name == m.name, f"{m.name}: spec.name={s.name!r}"
        assert tuple(s.applied_layers) == tuple(m.applied_layers), m.name
        assert tuple(s.consumes) == tuple(m.consumes), m.name
        assert tuple(s.emits) == tuple(m.emits), m.name
        assert s.tier in KNOWN_TIERS, f"{m.name}: tier={s.tier!r}"


def test_primary_secondary_membership_matches_spec_tier():
    from duecare.chat.harnesses import PRIMARY_HARNESSES, SECONDARY_HARNESSES
    for m in PRIMARY_HARNESSES:
        assert m.spec.tier == "primary", m.name
    for m in SECONDARY_HARNESSES:
        assert m.spec.tier == "secondary", m.name


def test_every_harness_adopts_baseharness():
    """Every harness exposes a `harness` singleton extending the thin BaseHarness, with
    attributes consistent with the module (the BaseHarness rollout is enforced here)."""
    from duecare.chat.harnesses.base import BaseHarness
    for m in _harnesses():
        h = getattr(m, "harness", None)
        assert isinstance(h, BaseHarness), f"{m.name}: missing a BaseHarness `harness` instance"
        assert h.name == m.name, m.name
        assert tuple(h.applied_layers) == tuple(m.applied_layers), m.name
        assert tuple(h.consumes) == tuple(m.consumes), m.name
        assert tuple(h.emits) == tuple(m.emits), m.name


# ---------------------------------------------------------------------------
# Primitive 2 -- the sub-primitives carried inside every spec
# ---------------------------------------------------------------------------

def test_every_model_target_conforms():
    for m in _harnesses():
        targets = list(m.spec.model_targets)
        n_default = 0
        for t in targets:
            tid, label, role = _field(t, "id"), _field(t, "label"), _field(t, "role")
            transport = _field(t, "transport")
            assert tid and label and role, f"{m.name}: incomplete model target {t}"
            assert transport in KNOWN_TRANSPORTS, f"{m.name}: unknown transport {transport!r}"
            n_default += 1 if _field(t, "default", False) else 0
        assert n_default <= 1, f"{m.name}: {n_default} default model targets (max 1)"


def test_every_logic_path_conforms():
    for m in _harnesses():
        for lp in m.spec.logic_paths:
            lid, label, steps = _field(lp, "id"), _field(lp, "label"), _field(lp, "steps")
            assert lid and label and steps, f"{m.name}: incomplete logic path {lp}"
            mc = _field(lp, "model_call", "none")
            assert mc in KNOWN_MODEL_CALL, f"{m.name}: logic_path model_call={mc!r}"


# ---------------------------------------------------------------------------
# Primitive 3 -- the canonical-schema objects agree on one input
# ---------------------------------------------------------------------------

_SAMPLE = (_ROOT / "packages" / "duecare-llm-chat" / "src" / "duecare" / "chat"
           / "static" / "samples" / "knowledge_object_sample.json")


def test_shipped_knowledge_object_is_a_valid_envelope():
    from duecare.chat.knowledge_taxonomy import validate_envelope
    env = json.loads(_SAMPLE.read_text(encoding="utf-8"))
    # structural envelope contract (schema_version, kebab id, content shape); the type's
    # catalog membership is enforced separately in test_workbench_inventory_integrity.
    ok, why = validate_envelope(env, known_types={env.get("knowledge_object_type")})
    assert ok, why


def test_same_knowledge_object_exports_to_conformant_okf():
    okf = _load_script("okf_export")
    env = json.loads(_SAMPLE.read_text(encoding="utf-8"))
    ok, why = okf.validate_okf(okf.render_okf(env))
    assert ok, why


def test_entity_edge_canonical_shape_normalizes():
    ee = _load_script("entity_edges")
    e = ee.normalize_edge({"subject_id": "a", "predicate": "parent_of", "object_id": "b"})
    assert e and {"subject_id", "predicate", "object_id", "source", "weight", "qualifier"} <= set(e)
    assert ee.normalize_edge({"subject_id": "a", "predicate": "p"}) is None   # incomplete -> rejected
    assert set(ee.KNOWN_PREDICATES)                                            # vocabulary present


def test_entity_record_converts_to_valid_ftm():
    ftm = _load_script("ftm_schema")
    e = ftm.to_ftm({"name": "Sailwind Trading FZE", "entity_type": "company", "jurisdiction": "AE"})
    assert e["schema"] == "Company" and e["id"] and e["properties"]["name"] == ["Sailwind Trading FZE"]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
