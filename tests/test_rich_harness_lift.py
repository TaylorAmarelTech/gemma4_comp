"""Tests for scripts/rich_harness_lift.py -- 3-arm richer-harness lift on a 0-100 scale (offline)."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# scripts/ on path so rich_harness_lift can import its sibling helpers (multi_judge, llm_generate)
sys.path.insert(0, str(_ROOT / "scripts"))
for _src in _ROOT.glob("packages/*/src"):
    sys.path.insert(0, str(_src))
rh = _load("rich_harness_lift", _ROOT / "scripts" / "rich_harness_lift.py")


def test_generate_reuses_two_arms_and_generates_only_full(tmp_path):
    prompts = [{"id": "P1", "text": "fee question one"}, {"id": "P2", "text": "fee question two"}]
    reuse = {("gemma4:31b", "P1", "baseline"): "B1", ("gemma4:31b", "P1", "harness_core"): "C1",
             ("gemma4:31b", "P2", "baseline"): "B2", ("gemma4:31b", "P2", "harness_core"): "C2"}
    generated: list[str] = []

    def fake_generate(model: str, prompt_in: str) -> str:
        generated.append(prompt_in)
        return "FULL reply with the corridor statute and ILO indicator"

    results_path = tmp_path / "results.jsonl"
    n = rh.generate_responses(prompts, ["gemma4:31b"], reuse=reuse, results_path=results_path,
                              generate=fake_generate, pace=0.0, max_tokens=10, log=lambda _m: None)
    rows = [json.loads(x) for x in results_path.read_text(encoding="utf-8").splitlines()]
    assert n == 6 and len(rows) == 6                       # 2 prompts x 3 arms
    # only the harness_full arm was generated; baseline + harness_core were reused (no model call)
    assert len(generated) == 2
    assert all("FULL reply" not in r["response"] for r in rows if r["arm"] != "harness_full")
    assert all(r["response"].startswith("FULL reply") for r in rows if r["arm"] == "harness_full")
    # resume: a second pass writes nothing new
    assert rh.generate_responses(prompts, ["gemma4:31b"], reuse=reuse, results_path=results_path,
                                 generate=fake_generate, pace=0.0, max_tokens=10, log=lambda _m: None) == 0


def test_judge_panel_0_100_and_self_family_excluded(tmp_path):
    results = [
        {"model": "gemma4:31b", "prompt_id": "P1", "arm": "baseline", "prompt_text": "q", "response": "BASE"},
        {"model": "gemma4:31b", "prompt_id": "P1", "arm": "harness_core", "prompt_text": "q", "response": "CORE"},
        {"model": "gemma4:31b", "prompt_id": "P1", "arm": "harness_full", "prompt_text": "q", "response": "FULL"},
    ]

    def fake_judge_caller(prompt: str, **_kw) -> str:
        # the candidate reply is appended after "ASSISTANT REPLY:"; score by which arm it is
        reply = prompt.rsplit("ASSISTANT REPLY:", 1)[-1]
        score = 90 if "FULL" in reply else 70 if "CORE" in reply else 40
        return json.dumps({"score": score})

    panel_path = tmp_path / "panel.jsonl"
    # one cross-family judge + one SAME-family judge (must be skipped for a gemma candidate)
    n = rh.judge_panel(results, ["gpt-oss:120b", "gemma-mini"], panel_path=panel_path,
                       judge_caller=fake_judge_caller, pace=0.0, log=lambda _m: None)
    cells = [json.loads(x) for x in panel_path.read_text(encoding="utf-8").splitlines()]
    assert n == 3 and len(cells) == 3                      # 3 arms x 1 eligible judge
    assert {c["judge"] for c in cells} == {"gpt-oss:120b"}  # gemma-mini excluded (self-family)
    assert all(0 <= c["score_0_100"] <= 100 for c in cells)
    by_arm = {c["arm"]: c["score_0_100"] for c in cells}
    assert by_arm == {"baseline": 40.0, "harness_core": 70.0, "harness_full": 90.0}


def test_pairwise_core_full_signed_preference(tmp_path):
    results = [
        {"model": "gemma4:31b", "prompt_id": "P1", "arm": "harness_core", "prompt_text": "q", "response": "CORE reply"},
        {"model": "gemma4:31b", "prompt_id": "P1", "arm": "harness_full", "prompt_text": "q", "response": "FULL reply"},
    ]

    def fake_pair_caller(prompt: str, **_kw) -> str:
        # judge_pair calls both orders; score by which reply sits in the B slot (+ = B safer)
        b_slot = prompt.rsplit("REPLY B:", 1)[-1]
        return json.dumps({"delta": 3 if "FULL" in b_slot else -3})   # full consistently safer by +3

    pw_path = tmp_path / "pairwise.jsonl"
    n = rh.pairwise_core_full(results, ["gpt-oss:120b", "gemma-mini"], pairwise_path=pw_path,
                              judge_caller=fake_pair_caller, pace=0.0, log=lambda _m: None)
    rows = [json.loads(x) for x in pw_path.read_text(encoding="utf-8").splitlines()]
    assert n == 1 and len(rows) == 1                       # 1 prompt x 1 eligible judge (gemma excluded)
    assert rows[0]["judge"] == "gpt-oss:120b" and rows[0]["delta"] == 3.0   # full preferred, bias-cancelled


def test_aggregate_pairwise_win_rate(tmp_path):
    rows = [
        {"model": "gemma4:31b", "prompt_id": "P1", "judge": "gpt-oss:120b", "delta": 2.0},
        {"model": "gemma4:31b", "prompt_id": "P1", "judge": "glm-5.2", "delta": 1.0},
        {"model": "gemma4:31b", "prompt_id": "P2", "judge": "gpt-oss:120b", "delta": -1.0},
        {"model": "gemma4:31b", "prompt_id": "P2", "judge": "glm-5.2", "delta": 0.0},
    ]
    agg = rh.aggregate_pairwise(rows, ["gpt-oss:120b", "glm-5.2"])
    r = agg["models"][0]
    assert r["n_prompts"] == 2
    assert r["panel_mean_delta"] == 0.5                    # mean(2,1,-1,0)
    assert r["win_rate_full"] == 50.0                      # P1 mean +1.5 > 0.05; P2 mean -0.5 not
    assert r["loss_rate_full"] == 50.0


def test_aggregate_lift_math(tmp_path):
    panel = []
    for j, base, core, full in [("gpt-oss:120b", 40, 70, 92), ("glm-5.2", 50, 75, 88)]:
        for pid in ("P1", "P2"):
            for arm, sc in (("baseline", base), ("harness_core", core), ("harness_full", full)):
                panel.append({"key": f"gemma4:31b|{pid}|{arm}", "model": "gemma4:31b",
                              "arm": arm, "prompt_id": pid, "judge": j, "score_0_100": sc})
    agg = rh.aggregate(panel, ["gpt-oss:120b", "glm-5.2"])
    row = agg["models"][0]
    assert row["panel_arm"]["baseline"] == 45.0           # (40+50)/2
    assert row["panel_arm"]["harness_full"] == 90.0        # (92+88)/2
    assert row["lift_full_vs_baseline"] == 45.0            # 90 - 45
    assert row["lift_full_vs_core"] == 17.5                # 90 - 72.5
    assert row["n_prompts"] == 2
