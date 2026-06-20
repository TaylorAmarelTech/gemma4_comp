"""Drift guard: the entity-intelligence counts cited in docs + the render page must match
the single source of truth (`scripts/entity_counts.compute_counts()`).

This is the same pattern as `test_doc_count_drift.py` (which guards the GREP/RAG counts):
if you add a registry / catalogue source, these tests fail until every surface is updated
(and the generated `entity_counts.json` regenerated) -- so a stale count can never ship.
Mirrors the real bug this prevents: a 32->34 change that had to be hand-fixed in 6 files.
"""
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


ec = _load("entity_counts", _ROOT / "scripts" / "entity_counts.py")
_C = ec.compute_counts()


def _fmt(n: int) -> str:
    return f"{n:,}"


def test_generated_json_matches_compute_counts():
    j = json.loads((_ROOT / "apps" / "duecare-ai.com" / "app" / "static" / "entity_counts.json")
                   .read_text(encoding="utf-8"))
    assert j == _C, "entity_counts.json is stale -- run `python scripts/entity_counts.py --write`"


#: file -> the literal count strings that MUST appear in it (derived from the live counts)
_R, _S, _P = _C["registries"], _C["config_specs"], _C["deterministic_resolvers"]
_L, _O = _fmt(_C["licensed_sources"]), str(_C["support_orgs"])
_EXPECT = {
    "apps/duecare-ai.com/app/templates/source-verification.html": [
        f">{_R}<", f">{_L}<", f">{_O}<",
        f"{_S} config specs + {_P} deterministic resolvers", f"{_R} total"],
    "docs/entity_intelligence_pipeline.md": [
        f"{_R} addressable registries", f"{_S} config specs", f"{_P} deterministic", _L, _O],
    "docs/entity_intelligence_complete_reference.md": [
        f"{_R} addressable registries", _L, _O],
    "README.md": [f"{_R} official government registries", f"{_L}-source"],
    "CLAUDE.md": [f"{_R}-registry acquisition cascade", f"{_L}-source"],
    "AGENTS.md": [f"{_R}-registry", f"{_L}-source"],
}


@pytest.mark.parametrize("relpath,needles", list(_EXPECT.items()))
def test_doc_counts_match_live(relpath, needles):
    text = (_ROOT / relpath).read_text(encoding="utf-8")
    missing = [n for n in needles if n not in text]
    assert not missing, (f"{relpath} has stale entity counts {missing} -- update it to match "
                         f"`python scripts/entity_counts.py` (and regenerate the JSON).")
