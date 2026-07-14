"""The --grader flag: judge_panel routes to the batched or the per-dimension grader.

Taylor's rigor rule is "a single prompt for EACH dimension". judge_components (batched) sends ONE
judge call scoring all components; judge_components_perdim sends ONE call PER component. This test
proves judge_panel honours the selected grader by counting judge_caller invocations per cell -- with
1 result row x 1 judge (= 1 cell): batched makes 1 call, per-dim makes 5 (v1: A-E). Offline; the judge
caller is a fake, no network.
"""
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


sys.path.insert(0, str(_ROOT / "scripts"))
for _src in _ROOT.glob("packages/*/src"):
    sys.path.insert(0, str(_src))
rh = _load("rich_harness_lift", _ROOT / "scripts" / "rich_harness_lift.py")

_RESULTS = [{"model": "candidate", "prompt_id": "D1", "arm": "baseline",
             "prompt_text": "q", "response": "a"}]
# a fake judge that returns every component key each call, so per-dim can extract whichever it asked for
_ALL_COMPS = '{"A":20,"B":15,"C":18,"D":8,"E":9,"score":70}'


def _counting_caller():
    calls: list[str] = []

    def caller(prompt, *, model, max_tokens=0, **kw):
        calls.append(prompt)
        return _ALL_COMPS

    return calls, caller


def test_batched_grader_is_one_call_for_all_dimensions(tmp_path):
    calls, caller = _counting_caller()
    n = rh.judge_panel(_RESULTS, ["judge"], panel_path=tmp_path / "panel.jsonl", judge_caller=caller,
                       pace=0.0, log=lambda _m: None)                 # default grader = batched
    assert n == 1
    assert len(calls) == 1                                            # one judge call scores all A-E


def test_perdim_grader_is_one_call_per_dimension(tmp_path):
    calls, caller = _counting_caller()
    panel_path = tmp_path / "panel.jsonl"
    n = rh.judge_panel(_RESULTS, ["judge"], panel_path=panel_path, judge_caller=caller,
                       pace=0.0, log=lambda _m: None, grader=rh.judge_components_perdim)
    assert n == 1
    assert len(calls) == 5                                            # one judge call PER dimension (A-E)
    assert json.loads(panel_path.read_text(encoding="utf-8"))["grader"] == "perdim"


def test_perdim_incomplete_cell_is_not_checkpointed_as_done(tmp_path):
    calls = []

    def caller(prompt, *, model, max_tokens=0, **_kwargs):
        key = next(k for k in "ABCDE" if f'"{k}"' in prompt)
        calls.append(key)
        return "not-json" if key == "D" else '{"' + key + '":1,"reason":"ok"}'

    panel_path = tmp_path / "panel.jsonl"
    logs = []
    n = rh.judge_panel(
        _RESULTS, ["judge"], panel_path=panel_path, judge_caller=caller,
        pace=0.0, log=logs.append, grader=rh.judge_components_perdim,
    )

    assert n == 0
    assert not panel_path.read_text(encoding="utf-8")
    assert calls.count("D") == 2
    assert any("incomplete per-dimension grade: missing D" in message for message in logs)


def test_perdim_sidecar_repairs_only_missing_dimension_and_prevents_duplicates(tmp_path):
    panel_path = tmp_path / "panel.jsonl"
    first_calls = []

    def first_caller(prompt, *, model, max_tokens=0, **_kwargs):
        key = next(k for k in "ABCDE" if f'"{k}"' in prompt)
        first_calls.append(key)
        return "not-json" if key == "D" else json.dumps({key: 10})

    assert rh.judge_panel(
        _RESULTS, ["judge"], panel_path=panel_path, judge_caller=first_caller,
        pace=0.0, log=lambda _m: None, grader=rh.judge_components_perdim,
    ) == 0
    assert first_calls.count("D") == 2
    cache_path = rh.component_cache_path(panel_path)
    assert cache_path.exists()
    assert b"WORKER" not in cache_path.read_bytes()
    assert b"ASSISTANT REPLY" not in cache_path.read_bytes()

    repair_calls = []

    def repair_caller(prompt, *, model, max_tokens=0, **_kwargs):
        key = next(k for k in "ABCDE" if f'"{k}"' in prompt)
        repair_calls.append(key)
        return json.dumps({key: 10})

    assert rh.judge_panel(
        _RESULTS, ["judge"], panel_path=panel_path, judge_caller=repair_caller,
        pace=0.0, log=lambda _m: None, grader=rh.judge_components_perdim,
    ) == 1
    assert repair_calls == ["D"]
    row = json.loads(panel_path.read_text(encoding="utf-8"))
    assert row["grader"] == "perdim"
    assert row["score_0_100"] == 50.0
    assert row["grade_input_sha256"] == rh.grade_input_sha256("q", "a")

    def must_not_call(*_args, **_kwargs):
        raise AssertionError("complete valid panel cell should resume without a judge call")

    assert rh.judge_panel(
        _RESULTS, ["judge"], panel_path=panel_path, judge_caller=must_not_call,
        pace=0.0, log=lambda _m: None, grader=rh.judge_components_perdim,
    ) == 0
    assert len(panel_path.read_text(encoding="utf-8").splitlines()) == 1


def test_judge_panel_selected_model_scope_does_not_grade_shared_results(tmp_path):
    results = [
        {"model": "active", "prompt_id": "D1", "arm": "baseline", "prompt_text": "q", "response": "a"},
        {"model": "historical", "prompt_id": "D1", "arm": "baseline", "prompt_text": "q", "response": "b"},
    ]
    calls = []

    def caller(prompt, *, model, max_tokens=0, **_kwargs):
        calls.append(prompt)
        return _ALL_COMPS

    panel_path = tmp_path / "panel.jsonl"
    assert rh.judge_panel(
        results, ["judge"], panel_path=panel_path, judge_caller=caller,
        pace=0.0, log=lambda _m: None, grader=rh.judge_components_perdim,
        selected_models=["active"], selected_prompt_texts={"D1": "q"},
    ) == 1
    assert len(calls) == 5
    assert json.loads(panel_path.read_text(encoding="utf-8"))["model"] == "active"


def test_exact_coverage_rejects_stale_prompt_and_accepts_bound_complete_cells(tmp_path):
    prompts = [{"id": "D1", "text": "q"}]
    results_path = tmp_path / "results.jsonl"
    rows = [
        {"model": "active", "prompt_id": "D1", "arm": arm, "prompt_text": "q", "response": f"a-{arm}"}
        for arm in rh.ARMS
    ]
    results_path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    panel_path = tmp_path / "panel.jsonl"
    calls, caller = _counting_caller()
    assert rh.judge_panel(
        rows, ["judge"], panel_path=panel_path, judge_caller=caller,
        pace=0.0, log=lambda _m: None, grader=rh.judge_components_perdim,
        selected_models=["active"], selected_prompt_texts={"D1": "q"},
    ) == 3
    assert len(calls) == 15

    complete = rh.compute_run_coverage(
        prompts, ["active"], ["judge"], results_path=results_path, panel_path=panel_path,
        rubric_version="v1", harness_version="h1", grader="perdim",
    )
    assert complete["complete"] is True
    assert complete["response_cells"] == {"expected": 3, "complete": 3, "missing": 0}
    assert complete["panel_cells"] == {"expected": 3, "complete": 3, "missing": 0}
    assert complete["dimension_outputs"]["complete_in_valid_panel_cells"] == 15

    stale = rh.compute_run_coverage(
        [{"id": "D1", "text": "changed q"}], ["active"], ["judge"],
        results_path=results_path, panel_path=panel_path,
        rubric_version="v1", harness_version="h1", grader="perdim",
    )
    assert stale["complete"] is False
    assert stale["response_cells"]["complete"] == 0
    assert stale["panel_cells"]["complete"] == 0


def test_require_complete_cli_returns_retryable_exit_then_zero_on_exact_closure(tmp_path, monkeypatch):
    prompt_path = tmp_path / "prompts.json"
    prompt_path.write_text(json.dumps([{"id": "D1", "text": "q"}]), encoding="utf-8")
    paths = {
        "results": tmp_path / "results.jsonl",
        "panel": tmp_path / "panel_perdim.jsonl",
        "pairwise": tmp_path / "pairwise.jsonl",
        "report": tmp_path / "report.md",
    }
    monkeypatch.setattr(rh, "run_paths_for_domain", lambda *_args, **_kwargs: paths)
    argv = [
        "--prompts", str(prompt_path), "--models", "active", "--judges", "judge",
        "--grader", "perdim", "--report-only", "--require-complete",
    ]

    assert rh.main(argv) == rh.INCOMPLETE_COVERAGE_EXIT
    incomplete = json.loads(rh.coverage_manifest_path(paths["panel"]).read_text(encoding="utf-8"))
    assert incomplete["status"] == "incomplete"

    result_rows = [
        {"model": "active", "prompt_id": "D1", "arm": arm, "prompt_text": "q", "response": f"a-{arm}"}
        for arm in rh.ARMS
    ]
    paths["results"].write_text(
        "".join(json.dumps(row) + "\n" for row in result_rows), encoding="utf-8",
    )
    panel_rows = []
    components = {"A": 20, "B": 15, "C": 20, "D": 10, "E": 10}
    for result in result_rows:
        panel_rows.append({
            "key": f"active|D1|{result['arm']}",
            "model": "active",
            "prompt_id": "D1",
            "arm": result["arm"],
            "judge": "judge",
            "score_0_100": 75.0,
            "components": components,
            "grader": "perdim",
            "grade_input_sha256": rh.grade_input_sha256("q", result["response"]),
        })
    paths["panel"].write_text(
        "".join(json.dumps(row) + "\n" for row in panel_rows), encoding="utf-8",
    )

    assert rh.main(argv) == 0
    complete = json.loads(rh.coverage_manifest_path(paths["panel"]).read_text(encoding="utf-8"))
    assert complete["status"] == "complete"
    assert complete["coverage"]["dimension_outputs"]["complete_in_valid_panel_cells"] == 15


def test_grader_none_defaults_to_batched_and_honours_monkeypatch(tmp_path, monkeypatch):
    """grader=None resolves to the module-global judge_components at CALL time, so a monkeypatch of it
    (the existing test suite's mechanism) still takes effect."""
    used = {}

    def fake_components(prompt, response, *, model, caller, domain_spec, rubric_version):
        used["hit"] = True
        return {"score": 88.0, **{k: 1.0 for k, _l, _m in rh.COMPONENTS}}

    monkeypatch.setattr(rh, "judge_components", fake_components)
    n = rh.judge_panel(_RESULTS, ["judge"], panel_path=tmp_path / "panel.jsonl", judge_caller=None,
                       pace=0.0, log=lambda _m: None)                 # grader=None -> monkeypatched batched
    assert n == 1 and used.get("hit") is True


def test_perdim_paths_isolate_panel_and_report_only():
    batched = rh.run_paths_for_domain("trafficking")
    perdim = rh.run_paths_for_domain("trafficking", grader="perdim")
    composed = rh.run_paths_for_domain(
        "trafficking", rubric_version="v2", harness_version="h2", grader="perdim",
    )

    assert perdim["results"] == batched["results"]
    assert perdim["pairwise"] == batched["pairwise"]
    assert perdim["panel"].name == "panel_perdim.jsonl"
    assert perdim["report"].name == "rich_harness_lift_100_perdim.md"
    assert composed["results"].name == "results_h2.jsonl"
    assert composed["pairwise"].name == "pairwise_h2.jsonl"
    assert composed["panel"].name == "panel_h2_v2_perdim.jsonl"
    assert composed["report"].name == "rich_harness_lift_100_h2_v2_perdim.md"
