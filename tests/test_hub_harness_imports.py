"""Hub-side harness contract: same shape as kernel side."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest


HUB_APP = Path(__file__).resolve().parents[1] / "apps" / "duecare-ai.com"
if str(HUB_APP) not in sys.path:
    sys.path.insert(0, str(HUB_APP))


@pytest.fixture(scope="module")
def hub_harnesses():
    from app.harnesses import all_harnesses
    return all_harnesses()


@pytest.fixture(scope="module")
def primary_harnesses():
    from app.harnesses import PRIMARY_HARNESSES
    return PRIMARY_HARNESSES


def test_hub_harness_exports_name(hub_harnesses):
    for h in hub_harnesses:
        assert isinstance(h.name, str) and h.name


def test_hub_harness_exports_applied_layers(hub_harnesses):
    for h in hub_harnesses:
        assert isinstance(h.applied_layers, tuple)


def test_hub_harness_exports_register_routes(hub_harnesses):
    for h in hub_harnesses:
        assert callable(getattr(h, "register_routes", None))


def test_hub_harness_consumes_emits_are_tuples(hub_harnesses):
    for h in hub_harnesses:
        assert isinstance(getattr(h, "consumes", None), tuple)
        assert isinstance(getattr(h, "emits", None), tuple)


def test_hub_primary_harnesses_include_core_surfaces(primary_harnesses):
    names = {h.name for h in primary_harnesses}
    assert {"curator", "sentinel", "submit"} <= names
