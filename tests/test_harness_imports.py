"""Contract smoke test: every harness exposes name + applied_layers + register_routes."""
from __future__ import annotations

import pytest

from duecare.chat.harnesses import all_harnesses


REQUIRED_LAYER_NAMES = {"persona", "grep", "rag", "tools", "online"}


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


def test_registry_has_exactly_four_harnesses():
    """Lock the count so a silent removal/addition is impossible."""
    names = {h.name for h in all_harnesses()}
    assert names == {"chat", "process", "extraction", "anonymization"}, \
        f"unexpected harness set: {sorted(names)}"
