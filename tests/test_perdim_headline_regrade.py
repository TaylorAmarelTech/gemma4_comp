"""Granular per-DIMENSION LLM re-grade of existing responses (the rigor-standard tool)."""
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


sys.path.insert(0, str(_ROOT / "scripts"))
for _s in _ROOT.glob("packages/*/src"):
    sys.path.insert(0, str(_s))
pr = _load("perdim_headline_regrade", _ROOT / "scripts" / "perdim_headline_regrade.py")


def _fake_caller():
    """A judge that scores the harnessed reply above the baseline on every component (so lift > 0),
    keyed on which single component the per-dim prompt asks for and whether the reply is 'harnessed'."""
    def caller(prompt, *, model, max_tokens=0, **kw):
        # the reply text is embedded after 'ASSISTANT REPLY:'; per-dim rubric asks for one component key
        harnessed = "HARNESSED" in prompt
        import re
        m = re.search(r'"([A-F])"\s*:', prompt)  # the single-key schema in the per-dim rubric
        key = m.group(1) if m else "A"
        val = 20 if harnessed else 5
        return f'{{"{key}": {val}, "reason": "x"}}'
    return caller


def test_regrade_reports_per_dimension_lift(monkeypatch):
    prompts = {"P1": "worker q", "P2": "worker q2"}
    responses = {
        "P1": {"baseline": "plain", "harness_core": "HARNESSED reply"},
        "P2": {"baseline": "plain", "harness_core": "HARNESSED reply"},
    }
    result = pr.regrade(["P1", "P2"], prompts, responses, model="gemma4:31b",
                        judges=["nvidia:openai/gpt-oss-120b"], caller=_fake_caller())
    pooled = result["pooled"]
    # every scored component (A-E) shows a positive lift (harnessed 20 - baseline 5 = +15)
    for k in ["A", "B", "C", "D", "E"]:
        assert pooled[k]["lift"] > 0, f"component {k} should lift"
    assert pooled["A"]["n"] == 2                          # two cells graded
    assert "score" in pooled                              # the assembled total is reported too


def test_self_family_judge_excluded():
    # a judge from the subject's own family is dropped (independence)
    result = pr.regrade([], {}, {}, model="gemma4:31b", judges=["gemma4:31b", "nvidia:openai/gpt-oss-120b"])
    assert "gemma4:31b" not in result["judges"]            # never grade your own family
    assert "nvidia:openai/gpt-oss-120b" in result["judges"]


def test_load_responses_filters_by_model(tmp_path):
    p = tmp_path / "results.jsonl"
    p.write_text(
        json.dumps({"model": "gemma4:31b", "prompt_id": "P1", "arm": "baseline", "response": "a"}) + "\n"
        + json.dumps({"model": "other", "prompt_id": "P1", "arm": "baseline", "response": "z"}) + "\n"
        + json.dumps({"model": "gemma4:31b", "prompt_id": "P1", "arm": "harness_core", "response": "b"}) + "\n",
        encoding="utf-8")
    by = pr.load_responses(p, "gemma4:31b")
    assert set(by["P1"]) == {"baseline", "harness_core"}   # only the requested model's arms
    assert by["P1"]["baseline"] == "a"
