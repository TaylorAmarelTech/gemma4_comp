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
import threading
import time
from concurrent.futures import ThreadPoolExecutor as RealThreadPoolExecutor
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
    monkeypatch.setattr(rl, "judge_components", lambda prompt, response, model, caller, **_kwargs: {
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


def test_large_workload_bounds_unfinished_futures_in_all_three_phases(tmp_path, monkeypatch):
    """The executor queue, not just its running threads, stays bounded at benchmark scale."""
    executors = []

    class RejectUnboundedExecutor(RealThreadPoolExecutor):
        def __init__(self, max_workers, *args, **kwargs):
            super().__init__(max_workers=max_workers, *args, **kwargs)
            self.worker_limit = max_workers
            self.futures = []
            self.max_unfinished = 0
            self.submitted = 0
            self._tracking_lock = threading.Lock()
            executors.append(self)

        def submit(self, fn, /, *args, **kwargs):
            with self._tracking_lock:
                unfinished = sum(not future.done() for future in self.futures)
                if unfinished >= self.worker_limit:
                    raise AssertionError(
                        f"executor queue exceeded {self.worker_limit} unfinished futures"
                    )
                future = super().submit(fn, *args, **kwargs)
                self.futures.append(future)
                self.submitted += 1
                self.max_unfinished = max(self.max_unfinished, unfinished + 1)
                return future

    monkeypatch.setattr(rl, "ThreadPoolExecutor", RejectUnboundedExecutor)
    monkeypatch.setattr(rl, "build_preambles", lambda: (
        (lambda text: "CORE:" + text), (lambda text: "FULL:" + text)))

    def brief_pause():
        # Keep workers busy long enough that eager submission would overflow immediately.
        time.sleep(0.0005)

    def fake_gen(model, prompt_in):
        brief_pause()
        return f"response:{model}:{prompt_in[-8:]}"

    def fake_components(prompt, response, model, caller, **_kwargs):
        brief_pause()
        return {"score": 88.0, **{key: 1.0 for key, _label, _maximum in rl.COMPONENTS}}

    def fake_pair(prompt, core, full, model, caller, **_kwargs):
        brief_pause()
        return 2.0

    monkeypatch.setattr(rl, "judge_components", fake_components)
    monkeypatch.setattr(rl, "judge_pair", fake_pair)

    prompt_count = 200
    prompts = [{"id": f"p{i}", "text": f"question {i}"} for i in range(prompt_count)]
    results_path = tmp_path / "results.jsonl"
    generated = rl.generate_responses(
        prompts, ["candidate"], reuse={}, results_path=results_path, generate=fake_gen,
        pace=0.0, max_tokens=10, log=lambda _message: None, concurrency=4)
    results = [json.loads(line) for line in results_path.read_text(encoding="utf-8").splitlines()]

    judged = rl.judge_panel(
        results, ["judge"], panel_path=tmp_path / "panel.jsonl", judge_caller=None,
        pace=0.0, log=lambda _message: None, concurrency=4)
    paired = rl.pairwise_core_full(
        results, ["judge"], pairwise_path=tmp_path / "pairwise.jsonl", judge_caller=None,
        pace=0.0, log=lambda _message: None, concurrency=4)

    assert generated == prompt_count * len(rl.ARMS)
    assert judged == generated
    assert paired == prompt_count
    assert [executor.submitted for executor in executors] == [generated, judged, paired]
    assert all(executor.max_unfinished <= executor.worker_limit == 4 for executor in executors)


def test_all_appenders_separate_a_crash_truncated_tail_without_truncating(tmp_path, monkeypatch):
    monkeypatch.setattr(rl, "build_preambles", lambda: (
        (lambda text: "CORE:" + text), (lambda text: "FULL:" + text)))
    monkeypatch.setattr(rl, "judge_components", lambda prompt, response, model, caller, **_kwargs: {
        "score": 88.0, **{key: 1.0 for key, _label, _maximum in rl.COMPONENTS}})
    monkeypatch.setattr(rl, "judge_pair", lambda *args, **kwargs: 2.0)

    results_path = tmp_path / "results.jsonl"
    panel_path = tmp_path / "panel.jsonl"
    pairwise_path = tmp_path / "pairwise.jsonl"
    partial = b'{"crash_partial":'
    for path in (results_path, panel_path, pairwise_path):
        path.write_bytes(partial)

    generated = rl.generate_responses(
        [{"id": "p1", "text": "question"}], ["candidate"], reuse={},
        results_path=results_path, generate=lambda model, prompt: "answer",
        pace=0.0, max_tokens=10, log=lambda _message: None, concurrency=2,
    )
    results = rl._load_jsonl_file(results_path)
    judged = rl.judge_panel(
        results, ["judge"], panel_path=panel_path, judge_caller=None,
        pace=0.0, log=lambda _message: None, concurrency=2,
    )
    paired = rl.pairwise_core_full(
        results, ["judge"], pairwise_path=pairwise_path, judge_caller=None,
        pace=0.0, log=lambda _message: None, concurrency=2,
    )

    assert (generated, judged, paired) == (3, 3, 1)
    for path, expected_rows in ((results_path, 3), (panel_path, 3), (pairwise_path, 1)):
        raw = path.read_bytes()
        assert raw.startswith(partial + b"\n{")
        assert raw.count(b"\n") == expected_rows + 1
        assert len(rl._load_jsonl_file(path)) == expected_rows
        before = raw
        assert rl._ensure_jsonl_append_boundary(path) is False
        assert path.read_bytes() == before


def test_streaming_jsonl_readers_tolerate_corrupt_and_non_object_lines(tmp_path):
    path = tmp_path / "mixed.jsonl"
    path.write_text(
        '{"model":"m","prompt_id":"p1","arm":"baseline"}\n'
        '{not-json}\n'
        '[]\n'
        '{"model":"m","prompt_id":"p2","arm":"harness_core"}',
        encoding="utf-8",
    )

    rows = rl._load_jsonl_file(path)
    done = rl._done_keys_for_harness(path, ("model", "prompt_id", "arm"), "h1")

    assert [row["prompt_id"] for row in rows] == ["p1", "p2"]
    assert done == {
        ("m", "p1", "baseline"),
        ("m", "p2", "harness_core"),
    }
