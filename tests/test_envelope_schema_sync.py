"""Guard: committed envelope_schema.json copies match the live catalog.

The schema is generated from KO_TYPE_CATALOG by scripts/build_envelope_schema.py
and committed twice (kernel static + hub static). If the catalog changes
without regenerating, every node would enforce a different contract than it
publishes -- this test fails first.
"""
from __future__ import annotations

import importlib
import json
import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SCRIPTS = _ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

builder = importlib.import_module("build_envelope_schema")

_COPIES = [
    _ROOT / "packages" / "duecare-llm-chat" / "src" / "duecare" / "chat"
    / "static" / "envelope_schema.json",
    _ROOT / "apps" / "duecare-ai.com" / "app" / "static" / "envelope_schema.json",
]


def test_committed_schema_copies_match_catalog() -> None:
    expected = builder.build()
    for copy in _COPIES:
        assert copy.exists(), f"missing committed schema copy: {copy}"
        actual = json.loads(copy.read_text(encoding="utf-8"))
        assert actual == expected, (
            f"{copy} is stale -- run `python scripts/build_envelope_schema.py`"
        )


def test_schema_copies_are_identical_bytes() -> None:
    texts = [c.read_text(encoding="utf-8") for c in _COPIES]
    assert texts[0] == texts[1]
