"""Offline --plan dry run: cost/coverage estimate without calling any model.

All three opt-in axes (rubric v2, harness h2, the benign-control merge) end on "needs a scheduled
versioned re-grade". --plan makes that re-grade costable first: it counts the INCREMENTAL model calls
(generation + judge + pairwise cells, self-family excluded, resumable from existing files) with no
Ollama call. This guards the counting math and the "no model was called" invariant.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


sys.path.insert(0, str(_ROOT / "scripts"))
for _src in _ROOT.glob("packages/*/src"):
    sys.path.insert(0, str(_src))
rh = _load("rich_harness_lift", _ROOT / "scripts" / "rich_harness_lift.py")


def _paths(tmp_path):
    return {"results": tmp_path / "results.jsonl", "panel": tmp_path / "panel.jsonl",
            "pairwise": tmp_path / "pairwise.jsonl", "report": tmp_path / "report.md"}


def test_plan_counts_all_cells_new_when_nothing_on_disk(tmp_path):
    prompts = [{"id": "P1", "text": "a"}, {"id": "P2", "text": "b"}]
    plan = rh.plan_run(prompts, ["gemma4:31b"], ["gpt-oss:120b", "glm-5.2"],
                       run_paths=_paths(tmp_path), reuse={})
    # 2 prompts x 1 model x 3 arms = 6 generation cells, none reusable, none on disk
    assert plan["gen_new_calls"] == 6
    assert plan["gen_reused"] == 0
    assert plan["gen_already_done"] == 0
    # 6 responses x 2 judges (both a different family from gemma) = 12 judge cells
    assert plan["judge_new_cells"] == 12
    assert plan["pairwise_new_cells"] == 0
    assert plan["total_new_model_calls"] == 18
    assert plan["n_prompts"] == 2 and plan["n_adversarial"] == 2 and plan["n_benign"] == 0
    assert plan["is_board_default"] is True
    assert plan["grader"] == "batched"
    assert plan["judge_calls_per_cell"] == 1
    assert plan["judge_new_calls"] == 12


def test_plan_credits_reuse_and_on_disk_rows(tmp_path):
    prompts = [{"id": "P1", "text": "a"}]
    paths = _paths(tmp_path)
    # baseline already generated on disk; harness_core reusable; only harness_full is a new call
    paths["results"].write_text(json.dumps(
        {"model": "gemma4:31b", "prompt_id": "P1", "arm": "baseline", "response": "x"}) + "\n",
        encoding="utf-8")
    reuse = {("gemma4:31b", "P1", "harness_core"): "cached"}
    plan = rh.plan_run(prompts, ["gemma4:31b"], ["gpt-oss:120b"], run_paths=paths, reuse=reuse)
    assert plan["gen_already_done"] == 1
    assert plan["gen_reused"] == 1
    assert plan["gen_new_calls"] == 1                      # harness_full only


def test_plan_excludes_self_family_judges(tmp_path):
    prompts = [{"id": "P1", "text": "a"}]
    # judge glm-5.2 shares the glm family with candidate glm-5.2 -> excluded; gpt-oss counts
    plan = rh.plan_run(prompts, ["glm-5.2"], ["glm-5.2", "gpt-oss:120b"],
                       run_paths=_paths(tmp_path), reuse={})
    assert plan["judge_new_cells"] == 3                    # 3 arms x only the gpt-oss judge


def test_plan_splits_intent_and_flags_opt_in(tmp_path):
    prompts = [{"id": "ADV1", "text": "a"},
               {"id": "BEN1", "text": "b", "intent": "benign"}]
    plan = rh.plan_run(prompts, ["gemma4:31b"], ["gpt-oss:120b"], run_paths=_paths(tmp_path),
                       reuse={}, rubric_version="v2", harness_version="h2")
    assert plan["n_adversarial"] == 1 and plan["n_benign"] == 1
    assert plan["is_board_default"] is False
    assert plan["rubric_version"] == "v2" and plan["harness_version"] == "h2"


def test_plan_pairwise_and_skip_judge(tmp_path):
    prompts = [{"id": "P1", "text": "a"}]
    with_pw = rh.plan_run(prompts, ["gemma4:31b"], ["gpt-oss:120b"], run_paths=_paths(tmp_path),
                          reuse={}, pairwise=True)
    assert with_pw["pairwise_new_cells"] == 1              # 1 prompt x 1 model x 1 judge
    assert with_pw["pairwise_calls_per_cell"] == 2          # both presentation orders
    assert with_pw["pairwise_new_calls"] == 2
    skip = rh.plan_run(prompts, ["gemma4:31b"], ["gpt-oss:120b"], run_paths=_paths(tmp_path),
                       reuse={}, skip_judge=True)
    assert skip["judge_new_cells"] == 0                    # no judging planned


def test_plan_rejects_unknown_versions(tmp_path):
    with pytest.raises(ValueError, match="unknown harness version"):
        rh.plan_run([{"id": "P1", "text": "a"}], ["m"], ["j"], run_paths=_paths(tmp_path),
                    reuse={}, harness_version="hZ")
    with pytest.raises(ValueError, match="unknown rubric version"):
        rh.plan_run([{"id": "P1", "text": "a"}], ["m"], ["j"], run_paths=_paths(tmp_path),
                    reuse={}, rubric_version="vZ")
    with pytest.raises(ValueError, match="unknown grader"):
        rh.plan_run([{"id": "P1", "text": "a"}], ["m"], ["j"], run_paths=_paths(tmp_path),
                    reuse={}, grader="unknown")


def test_plan_counts_underlying_per_dimension_calls_by_rubric(tmp_path):
    prompts = [{"id": "P1", "text": "a"}]
    v1 = rh.plan_run(prompts, ["gemma4:31b"], ["gpt-oss:120b"],
                     run_paths=_paths(tmp_path), reuse={}, grader="perdim")
    assert v1["judge_new_cells"] == 3
    assert v1["judge_calls_per_cell"] == 5
    assert v1["judge_new_calls"] == 15
    assert v1["total_new_model_calls"] == 18               # 3 generation + 15 judging
    assert v1["is_board_default"] is False

    v2 = rh.plan_run(prompts, ["gemma4:31b"], ["gpt-oss:120b"],
                     run_paths=_paths(tmp_path), reuse={}, grader="perdim", rubric_version="v2")
    assert v2["judge_calls_per_cell"] == 6                  # A-E plus separate F channel
    assert v2["judge_new_calls"] == 18
    assert v2["total_new_model_calls"] == 21


def test_perdim_resume_ignores_batched_panel_but_shares_generation(tmp_path):
    prompts = [{"id": "P1", "text": "a"}]
    shared_results = tmp_path / "results.jsonl"
    shared_pairwise = tmp_path / "pairwise.jsonl"
    batched = {
        "results": shared_results,
        "panel": tmp_path / "panel.jsonl",
        "pairwise": shared_pairwise,
        "report": tmp_path / "report.md",
    }
    perdim = {
        "results": shared_results,
        "panel": tmp_path / "panel_perdim.jsonl",
        "pairwise": shared_pairwise,
        "report": tmp_path / "report_perdim.md",
    }
    shared_results.write_text("\n".join(json.dumps({
        "model": "gemma4:31b", "prompt_id": "P1", "arm": arm, "response": "done",
    }) for arm in rh.ARMS) + "\n", encoding="utf-8")
    batched["panel"].write_text("\n".join(json.dumps({
        "model": "gemma4:31b", "prompt_id": "P1", "arm": arm, "judge": "gpt-oss:120b",
        "score_0_100": 80,
    }) for arm in rh.ARMS) + "\n", encoding="utf-8")

    batched_plan = rh.plan_run(prompts, ["gemma4:31b"], ["gpt-oss:120b"],
                               run_paths=batched, reuse={})
    perdim_plan = rh.plan_run(prompts, ["gemma4:31b"], ["gpt-oss:120b"],
                              run_paths=perdim, reuse={}, grader="perdim")

    assert batched_plan["gen_already_done"] == perdim_plan["gen_already_done"] == 3
    assert batched_plan["judge_new_cells"] == 0
    assert perdim_plan["judge_new_cells"] == 3
    assert perdim_plan["judge_new_calls"] == 15


def test_format_plan_states_no_model_was_called_and_scope():
    plan = rh.plan_run([{"id": "P1", "text": "a"}], ["gemma4:31b"], ["gpt-oss:120b"],
                       run_paths={"results": Path("reports/rich_lift/results.jsonl"),
                                  "panel": Path("reports/rich_lift/panel.jsonl"),
                                  "pairwise": Path("reports/rich_lift/pairwise.jsonl"),
                                  "report": Path("docs/research/rich_harness_lift_100.md")},
                       reuse={})
    text = rh.format_plan(plan)
    assert "NO model was called" in text
    assert "BOARD DEFAULT (v1/h1)" in text
    assert "Grader: batched (1 component judge call per panel cell)" in text
    assert "TOTAL" in text

    opt_in = rh.plan_run([{"id": "P1", "text": "a"}], ["gemma4:31b"], ["gpt-oss:120b"],
                         run_paths={"results": Path("reports/rich_lift/results_h2.jsonl"),
                                    "panel": Path("reports/rich_lift/panel_h2_v2.jsonl"),
                                    "pairwise": Path("reports/rich_lift/pairwise_h2.jsonl"),
                                    "report": Path("docs/research/rich_harness_lift_100_h2_v2.md")},
                         reuse={}, rubric_version="v2", harness_version="h2")
    assert "ISOLATED (h2/v2)" in rh.format_plan(opt_in)


def test_format_plan_redacts_private_external_path_names(tmp_path):
    plan = rh.plan_run(
        [{"id": "P1", "text": "a"}],
        ["gemma4:31b"],
        ["gpt-oss:120b"],
        run_paths={
            "results": tmp_path / "worker@example.invalid-results.jsonl",
            "panel": tmp_path / "panel.jsonl",
            "pairwise": tmp_path / "pairwise.jsonl",
            "report": tmp_path / "C-1234567890-report.md",
        },
        reuse={},
    )
    text = rh.format_plan(plan)

    assert "external/custom_or_invalid" in text
    assert "worker@example.invalid" not in text
    assert "C-1234567890" not in text


def test_main_plan_calls_no_model_and_writes_nothing(tmp_path, monkeypatch, capsys):
    prompt_path = tmp_path / "promptset.json"
    prompt_path.write_text(json.dumps({"domain": "trafficking",
                                       "prompts": [{"id": "P1", "text": "a"}, {"id": "P2", "text": "b"}]}),
                           encoding="utf-8")
    paths = _paths(tmp_path)
    monkeypatch.setattr(rh, "run_paths_for_domain", lambda *a, **k: paths)

    def _boom(*a, **k):  # any model call is a test failure
        raise AssertionError("--plan must not call a model")

    monkeypatch.setattr(rh, "ollama_chat", _boom)
    rc = rh.main(["--prompts", str(prompt_path), "--plan", "--require-complete",
                  "--models", "gemma4:31b",
                  "--judges", "gpt-oss:120b", "--reuse", str(tmp_path / "none.jsonl")])
    out = capsys.readouterr().out
    assert rc == 0
    assert "run plan (dry run" in out
    assert "TOTAL" in out
    assert not paths["results"].exists()                  # nothing generated
    assert not paths["panel"].exists()                    # nothing graded
    assert not paths["report"].exists()                   # nothing written
    assert not rh.coverage_manifest_path(paths["panel"]).exists()


def test_main_planned_call_guard_blocks_before_model_or_artifact(tmp_path, monkeypatch, capsys):
    prompt_path = tmp_path / "promptset.json"
    prompt_path.write_text(json.dumps({"domain": "trafficking",
                                       "prompts": [{"id": "P1", "text": "a"}]}),
                           encoding="utf-8")
    paths = _paths(tmp_path)
    monkeypatch.setattr(rh, "run_paths_for_domain", lambda *a, **k: paths)

    def _boom(*a, **k):
        raise AssertionError("the startup guard must run before any model call")

    monkeypatch.setattr(rh, "provider_chat", _boom)
    rc = rh.main(["--prompts", str(prompt_path), "--max-planned-model-calls", "0",
                  "--models", "gemma4:31b", "--judges", "gpt-oss:120b",
                  "--reuse", str(tmp_path / "none.jsonl")])
    captured = capsys.readouterr()

    assert rc == rh.BUDGET_EXCEEDED_EXIT
    assert "startup guard blocked the run" in captured.err
    assert "No model was called" in captured.err
    assert not paths["results"].exists()
    assert not paths["panel"].exists()
    assert not paths["report"].exists()
    assert not rh.coverage_manifest_path(paths["panel"]).exists()


def test_planned_call_budget_uses_cli_then_environment():
    assert rh.planned_model_call_budget(7, {"DUECARE_MAX_PLANNED_MODEL_CALLS": "2"}) == 7
    assert rh.planned_model_call_budget(None, {"DUECARE_MAX_PLANNED_MODEL_CALLS": "2"}) == 2
    assert rh.planned_model_call_budget(None, {}) is None
    with pytest.raises(ValueError, match="non-negative integer"):
        rh.planned_model_call_budget(None, {"DUECARE_MAX_PLANNED_MODEL_CALLS": "many"})
