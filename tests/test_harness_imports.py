"""Contract smoke test: every harness exposes the full self-describing surface."""
from __future__ import annotations

import pytest

from duecare.chat.app import KO_BRANCHES
from duecare.chat.harnesses import PRIMARY_HARNESSES, all_harnesses


REQUIRED_LAYER_NAMES = {
    "persona", "grep", "rag", "tools", "official_sources", "online",
}
VALID_KO_TYPES = set(KO_BRANCHES.keys())


@pytest.mark.parametrize("harness", all_harnesses(), ids=lambda h: h.name)
def test_harness_exports_name(harness):
    assert isinstance(harness.name, str) and harness.name, \
        f"{harness} must export a non-empty `name` string"


@pytest.mark.parametrize("harness", all_harnesses(), ids=lambda h: h.name)
def test_harness_exports_applied_layers(harness):
    assert hasattr(harness, "applied_layers"), \
        f"{harness.name} must export `applied_layers`"
    al = harness.applied_layers
    assert isinstance(al, tuple), \
        f"{harness.name}.applied_layers must be a tuple (got {type(al).__name__})"
    for layer in al:
        assert layer in REQUIRED_LAYER_NAMES, (
            f"{harness.name}.applied_layers contains unknown layer "
            f"{layer!r}; allowed: {sorted(REQUIRED_LAYER_NAMES)}"
        )


@pytest.mark.parametrize("harness", all_harnesses(), ids=lambda h: h.name)
def test_harness_exports_register_routes(harness):
    assert callable(getattr(harness, "register_routes", None)), \
        f"{harness.name} must export a callable `register_routes(app)`"


@pytest.mark.parametrize("harness", all_harnesses(), ids=lambda h: h.name)
def test_harness_consumes_are_valid_ko_types(harness):
    """Every entry in consumes must be a real KO type from KO_BRANCHES."""
    consumes = getattr(harness, "consumes", None)
    if consumes is None:
        return
    assert isinstance(consumes, tuple), \
        f"{harness.name}.consumes must be a tuple"
    for ko_type in consumes:
        assert ko_type in VALID_KO_TYPES, (
            f"{harness.name}.consumes contains unknown KO type "
            f"{ko_type!r}; allowed: {sorted(VALID_KO_TYPES)}"
        )


@pytest.mark.parametrize("harness", all_harnesses(), ids=lambda h: h.name)
def test_harness_emits_are_valid_ko_types(harness):
    """Every entry in emits must be a real KO type from KO_BRANCHES."""
    emits = getattr(harness, "emits", None)
    if emits is None:
        return
    assert isinstance(emits, tuple), \
        f"{harness.name}.emits must be a tuple"
    for ko_type in emits:
        assert ko_type in VALID_KO_TYPES, (
            f"{harness.name}.emits contains unknown KO type "
            f"{ko_type!r}; allowed: {sorted(VALID_KO_TYPES)}"
        )


VALID_CAPABILITIES = {"multi_turn", "streaming", "function_calling", "multimodal"}


@pytest.mark.parametrize("harness", all_harnesses(), ids=lambda h: h.name)
def test_harness_capabilities_are_valid(harness):
    """If a harness declares capabilities, every entry must be a known capability."""
    caps = getattr(harness, "capabilities", None)
    if caps is None:
        return
    assert isinstance(caps, (tuple, dict)), \
        f"{harness.name}.capabilities must be a tuple or dict"
    cap_names = caps.keys() if isinstance(caps, dict) else caps
    valid = VALID_CAPABILITIES | {
        "sanitize_query",
        "block_query",
        "verify_search_results",
        "score_source_quality",
        "detect_deanonymization_risk",
    }
    for cap in cap_names:
        assert cap in valid, (
            f"{harness.name}.capabilities contains unknown capability "
            f"{cap!r}; allowed: {sorted(valid)}"
        )


def test_primary_registry_locked():
    """The required primary safety surfaces must be present.

    Additional primary harnesses are allowed; this avoids a brittle exact-count
    assertion every time a new safety gate is added.
    """
    names = {h.name for h in PRIMARY_HARNESSES}
    required = {
        "chat",
        "process",
        "extraction",
        "anonymization",
        "search_safety",
        "post_search_verification",
    }
    assert required.issubset(names), \
        f"primary harness set is missing required surfaces: {sorted(required - names)}"
