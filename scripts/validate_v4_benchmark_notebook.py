#!/usr/bin/env python
"""scripts/validate_v4_benchmark_notebook.py

Local smoke test for kaggle/04-task-notebook-fresh/task_notebook.ipynb.

What this catches BEFORE we push to Kaggle:
  - Code cells with syntax errors.
  - Code cells that crash with an exception under a mock kbench.
  - The per-row + per-dim summary cell producing 0 rows when given
    a healthy mock Runs collection (regression: the user has seen
    this fail twice on Kaggle).
  - The stale-cache guard correctly raising SystemExit when the Runs
    collection is empty.
  - The published v4_per_dim_results.json artifact missing required
    fields.

Exits 0 on success, 1 on failure. Designed to run in `make verify-all`
alongside the structural validator at scripts/validate_benchmark.py.

We do NOT call the real `kaggle_benchmarks` package, GitHub raw, or
any network. The two rubric JSON fetches are served from the local
on-disk files; kbench is substituted with a mock that records calls
and returns canned data.
"""
from __future__ import annotations

import json
import pathlib
import sys
import types
import unittest.mock

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
NOTEBOOK_PATH = (
    REPO_ROOT
    / "kaggle"
    / "04-task-notebook-fresh"
    / "task_notebook.ipynb"
)


def _notebook_code_cells() -> list[str]:
    nb = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))
    out: list[str] = []
    for cell in nb["cells"]:
        if cell.get("cell_type") != "code":
            continue
        src = cell.get("source", "")
        if isinstance(src, list):
            src = "".join(src)
        out.append(src)
    return out


class _MockAssertionResult:
    def __init__(self, passed: bool) -> None:
        self.passed = passed
        self.expectation = "mock-expectation"


class _MockAssessment:
    def __init__(self, n: int, all_pass: bool = True) -> None:
        self.results = [_MockAssertionResult(all_pass) for _ in range(n)]


class _MockRun:
    """One record mirroring what kbench.runs.Runs yields. The summary
    cell extracts row_id from getattr(self, 'row_id') / 'id' / name."""

    def __init__(
        self,
        row_id: str,
        llm_id: str,
        passed: bool,
        failed_dim_ids: list[str] | None = None,
        veto_dim_ids: list[str] | None = None,
        err: str | None = None,
    ) -> None:
        self.row_id = row_id
        self.id = row_id
        self.name = f"row_id={row_id} llm={llm_id}"
        self.params = {"row_id": row_id}
        self.passed = passed
        self.error_message = err
        self.llm_id = llm_id
        self.assertion_failures = []
        for d in failed_dim_ids or []:
            af = types.SimpleNamespace(
                passed=False,
                expectation=f"dim={d} cluster=ethical_framing -- mock",
            )
            self.assertion_failures.append(af)
        for v in veto_dim_ids or []:
            af = types.SimpleNamespace(
                passed=False,
                expectation=f"HARD VETO: dimension '{v}' failed.",
            )
            self.assertion_failures.append(af)


class _MockRuns:
    def __init__(self, runs: list[_MockRun]) -> None:
        self.runs = runs

    def __iter__(self):
        return iter(self.runs)

    def __len__(self) -> int:
        return len(self.runs)

    def as_dataframe(self):
        raise KeyError("None of ['run_id'] are in the columns")


class _MockTask:
    def __init__(self, name: str) -> None:
        self.name = name
        self._runs: list[_MockRun] = []

    def evaluate(self, llm, evaluation_data, **kwargs):  # noqa: ARG002
        runs: list[_MockRun] = []
        rows = list(evaluation_data.to_dict("records"))
        for i, row in enumerate(rows):
            failing_dims = ["legal_specificity"] if i % 2 == 1 else []
            veto = ["harm_enablement_check"] if i % 5 == 0 and i > 0 else []
            runs.append(
                _MockRun(
                    row_id=row["row_id"],
                    llm_id="google/gemini-3-5",
                    passed=(i % 2 == 0) and not veto,
                    failed_dim_ids=failing_dims,
                    veto_dim_ids=veto,
                )
            )
        return _MockRuns(runs)


def _make_mock_kbench(empty_runs: bool = False):
    kbench = types.SimpleNamespace()
    kbench.judge_llm = types.SimpleNamespace(model_id="mock/judge-llm")
    kbench.llm = types.SimpleNamespace(model_id="google/gemini-3-5")

    def task_decorator(name: str):
        def _wrap(fn):
            mock_task = _MockTask(name)
            if empty_runs:
                mock_task.evaluate = (  # type: ignore[method-assign]
                    lambda llm, evaluation_data, **kw: _MockRuns([])
                )
            mock_task.fn = fn
            return mock_task

        return _wrap

    kbench.task = task_decorator

    def _assess_with_judge(criteria, response_text, judge_llm):  # noqa: ARG001
        return _MockAssessment(n=len(criteria), all_pass=True)

    def _assert_true(passed, expectation=""):  # noqa: ARG001
        return None

    kbench.assertions = types.SimpleNamespace(
        assess_response_with_judge=_assess_with_judge,
        assert_true=_assert_true,
    )
    kbench.runs = types.SimpleNamespace(Runs=_MockRuns)
    return kbench


def _exec_cells(cells: list[str], kbench_mock) -> dict:
    """Execute every code cell sequentially in a shared namespace.

    Stubs urllib.request.urlopen so the rubric fetch reads on-disk
    JSON instead of hitting GitHub. Returns the resulting namespace.
    """
    import io

    ns: dict = {"__name__": "__notebook__"}

    rubric_dir = (
        REPO_ROOT
        / "packages"
        / "duecare-llm-chat"
        / "src"
        / "duecare"
        / "chat"
        / "harness"
    )

    def fake_urlopen(url: str, *args, **kwargs):  # noqa: ARG001
        fname = url.rsplit("/", 1)[-1]
        path = rubric_dir / fname
        data = path.read_bytes()

        class _Resp:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def read(self):
                return data

        return _Resp()

    fake_module = types.ModuleType("kaggle_benchmarks")
    fake_module.task = kbench_mock.task
    fake_module.llm = kbench_mock.llm
    fake_module.judge_llm = kbench_mock.judge_llm
    fake_module.assertions = kbench_mock.assertions
    fake_module.runs = kbench_mock.runs

    buf = io.StringIO()
    saved_modules = sys.modules.get("kaggle_benchmarks")
    sys.modules["kaggle_benchmarks"] = fake_module
    saved_stdout = sys.stdout
    try:
        sys.stdout = buf
        with unittest.mock.patch(
            "urllib.request.urlopen", side_effect=fake_urlopen
        ):
            ns["display"] = lambda *a, **kw: None
            for i, src in enumerate(cells):
                # Skip IPython magic-only cells (e.g. "%choose ...").
                # These run inside Jupyter but `compile()` won't parse
                # them. A cell is considered magic-only if every
                # non-empty, non-comment line starts with % or !.
                meaningful_lines = [
                    ln.strip()
                    for ln in src.splitlines()
                    if ln.strip() and not ln.strip().startswith("#")
                ]
                if meaningful_lines and all(
                    ln.startswith(("%", "!")) for ln in meaningful_lines
                ):
                    continue
                try:
                    compile(src, f"<cell {i}>", "exec")
                except SyntaxError as exc:
                    raise AssertionError(
                        f"cell {i} has SyntaxError: {exc}"
                    ) from exc
                try:
                    exec(src, ns)  # noqa: S102
                except SystemExit as exc:
                    ns["__stale_cache_exit__"] = True
                    ns["__stale_cache_exit_arg__"] = str(exc)
                    break
    finally:
        sys.stdout = saved_stdout
        if saved_modules is None:
            sys.modules.pop("kaggle_benchmarks", None)
        else:
            sys.modules["kaggle_benchmarks"] = saved_modules
    ns["__captured_stdout__"] = buf.getvalue()
    return ns


def _check_happy_path(cells: list[str]) -> list[str]:
    failures: list[str] = []
    kbench_mock = _make_mock_kbench(empty_runs=False)
    ns = _exec_cells(cells, kbench_mock)

    rr = ns.get("RUN_RECORDS")
    if not rr:
        failures.append("happy path: RUN_RECORDS is empty after evaluate()")
    elif len(rr) < 5:
        failures.append(
            f"happy path: RUN_RECORDS too small ({len(rr)} entries)"
        )

    per_row = ns.get("per_row_verdict")
    if not isinstance(per_row, dict) or not per_row:
        failures.append("happy path: per_row_verdict is empty")

    per_dim_summary = ns.get("per_dim_summary")
    if not isinstance(per_dim_summary, list) or not per_dim_summary:
        failures.append("happy path: per_dim_summary not populated")
    else:
        legal = [
            r for r in per_dim_summary if r["dim_id"] == "legal_specificity"
        ]
        if not legal:
            failures.append(
                "happy path: legal_specificity missing from per_dim_summary"
            )
        else:
            if legal[0]["pass_pct"] >= 100.0:
                failures.append(
                    "happy path: legal_specificity pass% should be "
                    "<100 (failures injected in mock)"
                )

    # Notebook prefers /kaggle/working when it exists on disk
    # (Windows resolves that path to C:\kaggle\working, which may
    # exist locally); otherwise falls back to CWD.
    candidates = [
        pathlib.Path("v4_per_dim_results.json"),
        pathlib.Path("/kaggle/working/v4_per_dim_results.json"),
    ]
    out = next((p for p in candidates if p.exists()), None)
    if out is None:
        failures.append(
            "happy path: v4_per_dim_results.json not written in "
            f"any of: {[str(p) for p in candidates]}"
        )
    else:
        try:
            doc = json.loads(out.read_text(encoding="utf-8"))
            for field in (
                "task_name",
                "rubric_version",
                "n_dims",
                "n_rows",
                "per_row_verdict",
                "per_dim_summary",
            ):
                if field not in doc:
                    failures.append(
                        f"happy path: artifact missing field {field!r}"
                    )
        finally:
            out.unlink(missing_ok=True)
    return failures


def _check_empty_runs_guard(cells: list[str]) -> list[str]:
    failures: list[str] = []
    kbench_mock = _make_mock_kbench(empty_runs=True)
    ns = _exec_cells(cells, kbench_mock)
    if not ns.get("__stale_cache_exit__"):
        failures.append(
            "empty runs: stale-cache guard did NOT raise SystemExit "
            "(the user would see a silent empty table)"
        )
    captured = ns.get("__captured_stdout__", "")
    if "Factory Reset" not in captured:
        failures.append(
            "empty runs: stale-cache message missing the "
            "'Factory Reset' recovery hint"
        )
    return failures


def main() -> int:
    if not NOTEBOOK_PATH.exists():
        print(f"FAIL: {NOTEBOOK_PATH} does not exist", file=sys.stderr)
        return 1
    cells = _notebook_code_cells()
    print(f"validating {NOTEBOOK_PATH.name}: {len(cells)} code cells")
    failures: list[str] = []
    failures.extend(_check_happy_path(cells))
    failures.extend(_check_empty_runs_guard(cells))
    if failures:
        print()
        print("FAIL:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("OK: notebook structure + happy path + stale-cache guard all valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
