"""Tests for scripts/llm_generate.py -- the LLM generation engine + propose-only staging.

Offline: the model call is injected as a fake, so no network / no API key is needed. Covers
JSON extraction (incl. fenced output from reasoning models), the injectable caller, the
triage-test task's parse+filter, and that staging carries the propose-only markers.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


llm = _load("llm_generate", _ROOT / "scripts" / "llm_generate.py")


def test_extract_json_handles_fences_bare_and_arrays():
    assert llm.extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert llm.extract_json('here you go: {"cases": []} thanks') == {"cases": []}
    assert llm.extract_json("[1, 2, 3]") == [1, 2, 3]
    assert llm.extract_json("no json at all") is None
    assert llm.extract_json("") is None


def test_complete_uses_injected_caller_and_passes_params():
    seen = {}

    def fake(prompt, **kw):
        seen.update(kw)
        seen["prompt"] = prompt
        return "MODEL OUTPUT"

    out = llm.complete("hello", model="kimi-k2.7-code", max_tokens=1500, caller=fake)
    assert out == "MODEL OUTPUT"
    assert seen["model"] == "kimi-k2.7-code" and seen["max_tokens"] == 1500
    assert seen["prompt"] == "hello"


def test_generate_triage_test_cases_parses_and_filters():
    def fake(prompt, **kw):
        # the second case has no text -> must be dropped
        return ('```json\n{"cases": ['
                '{"text": "Pay a one-time placement fee to start.", "hidden_signal": "illegal fee"},'
                '{"hidden_signal": "no text here"}]}\n```')

    cases = llm.generate_triage_test_cases(2, caller=fake)
    assert len(cases) == 1
    assert cases[0]["text"].startswith("Pay a one-time") and cases[0]["hidden_signal"] == "illegal fee"


def test_generate_returns_empty_on_unparseable_output():
    assert llm.generate_triage_test_cases(3, caller=lambda p, **kw: "sorry, no json") == []


def test_prompt_mutations_inject_seed_and_stamp_it():
    def fake(prompt, **kw):
        assert "my custom seed" in prompt                # the seed reaches the prompt
        return '{"variants": [{"variant": "kindly waive the fee?", "technique": "politeness"}]}'

    out = llm.generate_prompt_mutations(1, caller=fake, seed="my custom seed")
    assert len(out) == 1 and out[0]["technique"] == "politeness"
    assert out[0]["seed"] == "my custom seed"            # stamped onto each variant


def test_knowledge_proposals_are_marked_unverified():
    def fake(prompt, **kw):
        return ('{"proposals": [{"observation": "some corridors cap recruitment fees",'
                '"claim_to_verify": "the exact cap", "source_type_to_check": "ministry circular"}]}')

    out = llm.generate_knowledge_proposals(1, caller=fake)
    assert len(out) == 1
    # the real-not-faked guardrail: a generated "fact" is never trusted, it is flagged for review
    assert out[0]["confidence"] == "unverified" and out[0]["_needs_source_verification"] is True


def test_outreach_drafts_parse():
    def fake(prompt, **kw):
        return ('{"drafts": [{"topic": "fees", "question": "What is the current cap?",'
                '"target_role": "NGO caseworker"}]}')

    out = llm.generate_outreach_drafts(1, caller=fake)
    assert len(out) == 1 and out[0]["question"] == "What is the current cap?"


def test_all_four_tasks_are_registered_and_callable():
    assert set(llm._TASKS) == {"triage-tests", "prompt-mutations",
                               "knowledge-proposals", "outreach-drafts"}
    for fn in llm._TASKS.values():
        assert callable(fn)


def test_stage_proposal_is_propose_only(tmp_path, monkeypatch):
    monkeypatch.setattr(llm, "PROPOSALS_DIR", tmp_path)
    items = [{"text": "synthetic ad", "hidden_signal": "passport retention"}]
    p = llm.stage_proposal(items, task="triage-tests", model="glm-5.2",
                           at="2026-06-20T00:00:00+00:00")
    assert p.parent == tmp_path                                  # staged under the proposals dir
    d = json.loads(p.read_text(encoding="utf-8"))
    assert d["_propose_only"] is True and d["_synthetic"] is True   # never auto-merged
    assert d["task"] == "triage-tests" and d["model"] == "glm-5.2"
    assert d["n"] == 1 and d["items"] == items
    assert d["generated_at"] == "2026-06-20T00:00:00+00:00"      # stamp is overridable for tests


def test_proposals_dir_is_under_gitignored_reports():
    # the staging path lives under reports/ (which .gitignore covers for *.json)
    assert llm.PROPOSALS_DIR.parent.name == "reports"
    assert llm.OLLAMA_CLOUD_BASE.startswith("https://ollama.com")   # cloud, not the local daemon
