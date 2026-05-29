"""Tests for the harness-lift benchmark meta-orchestrator.

Covers scripts/harness_lift_benchmark.py with injected fakes (no model/keys),
so the orchestration logic (per-target arms, lift computation, skip + error
resilience) is verified deterministically.
"""
from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = str(Path(__file__).resolve().parents[1] / "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import harness_lift_benchmark as hlb  # noqa: E402


def _grep(text, **_k):
    if "loan" in text:
        return {"hits": [{"rule": "r1", "severity": "high",
                          "citation": "ILO C029", "indicator": "debt bondage"}]}
    return {"hits": []}


def _rag(text, top_k=4):
    return {"docs": [{"id": "d1", "title": "T", "snippet": "s"}]}


def _resolve_positive(_target):
    # harnessed prompt (carries the grounding preamble) yields a better answer
    def mc(prompt, **_kw):
        return "harnessed-good" if "SAFETY GROUNDING" in prompt else "baseline-weak"
    return mc


def _grade(_prompt, resp):
    return 0.9 if "good" in resp else 0.4


def test_run_benchmark_reports_positive_lift():
    cfg = {
        "targets": [{"name": "gemini-3.5", "provider": "google_gemini"},
                    {"name": "opus-4.8", "provider": "anthropic"}],
        "prompts": [{"id": "p1", "text": "the agency gave me a loan"},
                    {"id": "p2", "text": "hello"}],
    }
    out = hlb.run_benchmark(cfg, grep_call=_grep, rag_call=_rag,
                            resolve_model_call=_resolve_positive, grade_fn=_grade)
    assert out["n_targets"] == 2 and out["n_prompts"] == 2
    # harnessed (0.9) - baseline (0.4) = 0.5 lift for every target
    assert out["ranked_by_lift"][0]["lift"] == 0.5
    for s in out["targets"]:
        assert s["status"] == "ok" and s["n"] == 2 and s["lift"] == 0.5


def test_unresolvable_target_is_skipped_not_fatal():
    out = hlb.run_benchmark(
        {"targets": [{"name": "no-key"}], "prompts": [{"id": "p", "text": "t"}]},
        grep_call=_grep, rag_call=_rag,
        resolve_model_call=lambda _t: None, grade_fn=_grade,
    )
    assert out["targets"][0]["status"] == "skipped"
    assert out["ranked_by_lift"] == []


def test_per_prompt_error_does_not_sink_target():
    def boom_grade(_p, _r):
        raise RuntimeError("grader down")

    out = hlb.run_benchmark(
        {"targets": [{"name": "t"}], "prompts": [{"id": "p", "text": "x"}]},
        grep_call=_grep, rag_call=_rag,
        resolve_model_call=_resolve_positive, grade_fn=boom_grade,
    )
    s = out["targets"][0]
    assert s["status"] == "ok" and s["n"] == 0 and s["n_errors"] == 1
