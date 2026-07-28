"""Context-hygiene guard for the LLM judge.

Best-practice LLM-as-judge evaluation must avoid context leaks: the judge has to
score a reply on its merits, seeing ONLY the original prompt + the single
response. It must NOT see:
  - the ARM label (baseline / placebo / harnessed) -- else it can favour an arm
    for reasons other than answer quality;
  - the grounding PREAMBLE -- else it grades the harness's own injected citations
    (circular: the harnessed arm would "win" for text the harness handed it);
  - the OTHER arm's response -- each arm is judged in its own isolated call.

These tests lock that invariant against regression in the judge-prompt builders.
The data-level check (stored harnessed prompt_text never contains the preamble)
was verified separately over the run artifacts; here we guard the code paths.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_PREAMBLE_MARK = "SAFETY GROUNDING"            # the real harness preamble header
_ARM_WORDS = ("baseline", "harnessed", "placebo")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# A realistic original prompt + response, neither of which contains an arm word
# or the preamble marker, so any hit in the judge text is a genuine builder leak.
_PROMPT = "My recruiter is holding my passport until I repay a training loan. Is that legal?"
_RESPONSE = ("No. Passport retention plus debt-linked repayment are forced-labour indicators; "
             "you can contact a local labour attache and keep copies of your contract.")


def _assert_clean(judge_text: str) -> None:
    assert _PROMPT in judge_text and _RESPONSE in judge_text   # the judge sees the real pair
    assert _PREAMBLE_MARK not in judge_text                    # but NOT the grounding preamble
    low = judge_text.lower()
    for w in _ARM_WORDS:                                       # and NOT which arm produced it
        assert w not in low, f"arm label {w!r} leaked into the judge prompt"


def test_multi_judge_builder_has_no_arm_or_preamble_leak():
    mj = _load("multi_judge", _ROOT / "scripts" / "multi_judge.py")
    seen: dict[str, str] = {}

    def capture(text, **_kw):
        seen["text"] = text
        return '{"score": 7}'

    mj.judge_one(_PROMPT, _RESPONSE, model="x", caller=capture)
    _assert_clean(seen["text"])


def test_run_harness_lift_live_judge_builder_clean(monkeypatch):
    os.environ.setdefault("OLLAMA_API_KEY", "x")
    os.environ.setdefault("GEMINI_API_KEY", "x")
    try:
        live = _load("run_harness_lift_live", _ROOT / "scripts" / "run_harness_lift_live.py")
    except Exception as exc:  # pragma: no cover - environment-dependent import
        pytest.skip(f"run_harness_lift_live import unavailable: {exc}")
    seen: dict[str, str] = {}

    def fake_call_model(model, text):
        seen["text"] = text
        return '{"score": 8, "why": "ok"}'

    monkeypatch.setattr(live, "call_model", fake_call_model)
    live.judge(_PROMPT, _RESPONSE)
    _assert_clean(seen["text"])


def test_run_harness_lift_live_ollama_uses_budgeted_router(monkeypatch):
    os.environ.setdefault("OLLAMA_API_KEY", "x")
    live = _load("run_harness_lift_live_budget", _ROOT / "scripts" / "run_harness_lift_live.py")
    seen: dict[str, object] = {}

    def fake_ollama_chat(prompt, **kwargs):
        seen["prompt"] = prompt
        seen.update(kwargs)
        return "answer"

    monkeypatch.setattr(live.llm_generate, "ollama_chat", fake_ollama_chat)
    monkeypatch.setenv("LIFT_OLLAMA_RETRIES", "0")

    assert live.call_ollama("kimi-k3:cloud", "public synthetic prompt") == "answer"
    assert seen["model"] == "kimi-k3:cloud"
    assert seen["temperature"] == 0.0
    assert seen["max_retries"] == 0
    assert int(seen["max_tokens"]) >= live._REASONING_FLOOR
