"""Contract test: every harness's optional tools module follows the same shape."""
from __future__ import annotations

import importlib

import pytest

from duecare.chat.harnesses import all_harnesses


REQUIRED_TOOL_KEYS = {"name", "description", "parameters"}


@pytest.mark.parametrize("harness", all_harnesses(), ids=lambda h: h.name)
def test_harness_tools_module_shape(harness):
    try:
        mod = importlib.import_module(f"duecare.chat.harnesses.{harness.name}.tools")
    except ImportError:
        return  # optional module
    assert callable(getattr(mod, "list_tools", None)), \
        f"{harness.name}/tools.py must expose list_tools()"
    tools = mod.list_tools()
    assert isinstance(tools, list), f"{harness.name}.list_tools() must return a list"
    for i, t in enumerate(tools):
        assert isinstance(t, dict), \
            f"{harness.name}.list_tools()[{i}] must be a dict"
        missing = REQUIRED_TOOL_KEYS - set(t.keys())
        assert not missing, \
            f"{harness.name}.list_tools()[{i}] missing keys: {sorted(missing)}"
        assert isinstance(t["name"], str) and t["name"], \
            f"{harness.name}.list_tools()[{i}].name must be a non-empty string"
        assert isinstance(t["description"], str) and t["description"], \
            f"{harness.name}.list_tools()[{i}].description must be a non-empty string"
        assert isinstance(t["parameters"], dict), \
            f"{harness.name}.list_tools()[{i}].parameters must be a dict"


def test_chat_harness_exposes_trafficking_tools():
    from duecare.chat.harnesses.chat import tools as chat_tools
    names = {t["name"] for t in chat_tools.list_tools()}
    expected = {
        "lookup_corridor_fee_cap", "lookup_fee_camouflage",
        "lookup_ilo_indicator", "lookup_ngo_intake", "lookup_ilo_convention",
    }
    assert expected.issubset(names), \
        f"chat missing tools: {sorted(expected - names)}"


def test_search_harness_exposes_web_search():
    from duecare.chat.harnesses.search import tools as search_tools
    names = {t["name"] for t in search_tools.list_tools()}
    assert "web_search" in names


def test_anonymization_tools_are_empty_by_design():
    """The anonymization harness must NOT expose tools to Gemma -- it's
    the PII gate. Regression guard against accidental tool addition."""
    from duecare.chat.harnesses.anonymization import tools as anon_tools
    assert anon_tools.list_tools() == [], \
        "anonymization tools must remain empty (trust boundary)"
