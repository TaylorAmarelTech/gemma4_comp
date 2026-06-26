"""Tests for the parallel generation/judging in scripts/rich_harness_lift.py (offline, no Ollama).

Verifies that the ThreadPoolExecutor refactor writes every cell exactly once (no corruption under
concurrent writes), stays resumable, and honours self-family exclusion -- all with stubbed model/judge
calls so nothing hits the network.
"""
from __future__ import annotations

import glob
import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "scripts"))
for _s in glob.glob(str(_ROOT / "packages" / "*" / "src")):
    sys.path.insert(0, _s)


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


rl = _load("rich_harness_lift", _ROOT / "scripts" / "rich_harness_lift.py")


def test_generate_responses_parallel_writes_all_and_resumes(tmp_path, monkeypatch):
    # stub the harness preambles (avoid importing duecare.chat.harness) + the model call
    monkeypatch.setattr(rl, "build_preambles", lambda: ((lambda t: "CORE:" + t), (lambda t: "FULL:" + t)))

    def fake_gen(model, prompt_in):
        return f"resp[{len(prompt_in)}]"

    prompts = [{"id": f"p{i}", "text": f"q{i}"} for i in range(6)]
    results = tmp_path / "results.jsonl"
    n = rl.generate_responses(prompts, ["m"], reuse={}, results_path=results, generate=fake_gen,
                              pace=0.0, max_tokens=10, log=lambda _m: None, concurrency=4)
    rows = [json.loads(line) for line in results.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert n == 18 and len(rows) == 18                       # 6 prompts x 3 arms, all written, uncorrupted
    keys = {(r["model"], r["prompt_id"], r["arm"]) for r in rows}
    assert len(keys) == 18                                   # every cell present exactly once
    assert all(r["response"].startswith("resp[") for r in rows)
    assert all("latency_s" in r for r in rows)               # generated rows carry latency

    # resumable: a second pass over the same store writes nothing new
    n2 = rl.generate_responses(prompts, ["m"], reuse={}, results_path=results, generate=fake_gen,
                               pace=0.0, max_tokens=10, log=lambda _m: None, concurrency=4)
    assert n2 == 0


def test_judge_panel_parallel_scores_and_excludes_self_family(tmp_path, monkeypatch):
    monkeypatch.setattr(rl, "judge_components", lambda prompt, response, model, caller: {
        "score": 88.0, **{k: 1 for k, _l, _m in rl.COMPONENTS}})
    results = [
        {"model": "gemma4:31b", "prompt_id": "p1", "arm": "baseline", "prompt_text": "q", "response": "a"},
        {"model": "gemma4:31b", "prompt_id": "p1", "arm": "harness_full", "prompt_text": "q", "response": "b"},
    ]
    panel = tmp_path / "panel.jsonl"
    nj = rl.judge_panel(results, ["gpt-oss:120b", "gemma4:31b"], panel_path=panel, judge_caller=None,
                        pace=0.0, log=lambda _m: None, concurrency=4)
    rows = [json.loads(line) for line in panel.read_text(encoding="utf-8").splitlines() if line.strip()]
    # gpt-oss judges both arms (2 rows); gemma4:31b is self-family -> excluded
    assert nj == 2 and len(rows) == 2
    assert all(r["judge"] == "gpt-oss:120b" and r["score_0_100"] == 88.0 for r in rows)
