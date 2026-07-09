"""The strengthened h2 grounded-response contract (anti-refusal-collapse phrasing).

The hard-collapse failure: the harness's safety framing trips a model's refusal reflex, converting a
correct grounded answer (baseline) into a bare "I can't help with that". The strengthened contract adds
two things Taylor asked for: (1) tell the model the injected context is REFERENCE material to answer
with, not a refusal trigger; (2) weigh all sources, resolve conflicts in favor of the migrant worker.
h2 is opt-in; h1 (the live board default) stays clean.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


sys.path.insert(0, str(_ROOT / "scripts"))
for _s in _ROOT.glob("packages/*/src"):
    sys.path.insert(0, str(_s))
rh = _load("rich_harness_lift", _ROOT / "scripts" / "rich_harness_lift.py")


def test_contract_has_anti_collapse_framing():
    c = rh.GROUNDED_REFUSAL_CONTRACT
    assert "REFERENCE CONTEXT" in c                       # context is to ANSWER with...
    assert "NOT a signal to refuse" in c                  # ...not a refusal trigger
    assert "WORST outcome" in c                           # a bare refusal is the worst outcome
    assert "full, grounded answer" in c                   # default is to answer


def test_contract_has_source_weighing_and_resolve_for_worker():
    c = rh.GROUNDED_REFUSAL_CONTRACT
    assert "Weigh ALL" in c
    assert "conflict" in c                                # handle conflicting sources
    assert "resolve in favor of protecting the migrant worker" in c


def test_contract_still_names_the_three_safety_deliverables():
    c = rh.GROUNDED_REFUSAL_CONTRACT
    assert "NEVER go silent" in c
    assert "exploitation indicator" in c
    assert "law or ILO convention" in c
    assert "protective resources" in c
    assert "legitimate worker-safety question" in c       # over-refusal side preserved


def test_h2_appends_contract_to_both_arms_h1_clean():
    core1, full1 = rh.build_preambles_for_domain(harness_version="h1")
    core2, full2 = rh.build_preambles_for_domain(harness_version="h2")
    assert rh.GROUNDED_REFUSAL_CONTRACT not in core1("q")  # h1 board default untouched
    assert rh.GROUNDED_REFUSAL_CONTRACT not in full1("q")
    assert core2("q").endswith(rh.GROUNDED_REFUSAL_CONTRACT)
    assert full2("q").endswith(rh.GROUNDED_REFUSAL_CONTRACT)
