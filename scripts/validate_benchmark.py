#!/usr/bin/env python
"""scripts/validate_benchmark.py

One-button validator for the DueCare Kaggle Community Benchmark surface.

Checks (in order, each prints its own pass/fail line):

  1. Syntax-check all main kernel.py files (01/02/04/A-00).
  2. Validate task_notebook.ipynb JSON structure + cell count + ROWS
     entries.
  3. Import duecare.chat.benchmark + count DEFAULT_FALLBACK_ROWS.
  4. Run selftest_benchmark.py --judge mock and assert exit 0.
  5. POST /api/grade-benchmark via FastAPI TestClient and assert the
     response shape.
  6. Cross-check task_notebook ROWS count <= DEFAULT_FALLBACK_ROWS
     count (drift between adapter + published notebook is the most
     common silent regression).

Exit non-zero on any failure so the script composes into Makefile /
pre-commit / CI gates.

Usage:
    python scripts/validate_benchmark.py
    python scripts/validate_benchmark.py --quiet     # only print FAIL lines
"""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
KERNEL_FILES = [
    REPO_ROOT / "kaggle/01-duecare-exploration-workbench/kernel.py",
    REPO_ROOT / "kaggle/02-live-demo/kernel.py",
    REPO_ROOT / "kaggle/04-kaggle-community-benchmark/kernel.py",
    REPO_ROOT / "kaggle/A-00-omni-experiment-workbench/kernel.py",
]
TASK_NOTEBOOKS = [
    REPO_ROOT / "kaggle/04-kaggle-community-benchmark/task_notebook.ipynb",
    REPO_ROOT / "kaggle/_archive/notebooks/04-task-notebook-publish/task_notebook.ipynb",
]


def _emit(kind: str, msg: str, *, quiet: bool) -> None:
    """Print a status line. ``kind`` is OK / FAIL / INFO."""
    if quiet and kind == "OK":
        return
    print(f"  [{kind:4s}] {msg}")


def check_kernel_syntax(*, quiet: bool) -> list[str]:
    print("[1/6] kernel.py syntax")
    failures: list[str] = []
    for path in KERNEL_FILES:
        if not path.exists():
            failures.append(f"missing: {path}")
            _emit("FAIL", f"{path.relative_to(REPO_ROOT)}: missing", quiet=quiet)
            continue
        try:
            compile(path.read_bytes(), str(path), "exec")
        except SyntaxError as exc:
            failures.append(f"{path}: {exc}")
            _emit("FAIL", f"{path.relative_to(REPO_ROOT)}: {exc}", quiet=quiet)
            continue
        _emit("OK", f"{path.relative_to(REPO_ROOT)}", quiet=quiet)
    return failures


def check_task_notebook(*, quiet: bool) -> tuple[list[str], int]:
    """Returns (failures, row_count_in_first_notebook)."""
    print("[2/6] task_notebook.ipynb structure")
    failures: list[str] = []
    row_count = -1
    for path in TASK_NOTEBOOKS:
        if not path.exists():
            failures.append(f"missing: {path}")
            _emit("FAIL", f"{path.relative_to(REPO_ROOT)}: missing", quiet=quiet)
            continue
        try:
            nb = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append(f"{path}: invalid JSON: {exc}")
            _emit("FAIL", f"{path.relative_to(REPO_ROOT)}: invalid JSON: {exc}", quiet=quiet)
            continue
        cells = nb.get("cells") or []
        if len(cells) < 5:
            failures.append(f"{path}: only {len(cells)} cells (expected >=5)")
            _emit("FAIL", f"{path.relative_to(REPO_ROOT)}: only {len(cells)} cells", quiet=quiet)
            continue
        rows_cell = None
        for c in cells:
            if c.get("cell_type") != "code":
                continue
            src = "".join(c.get("source") or [])
            if src.lstrip().startswith("ROWS = ["):
                rows_cell = src
                break
        if rows_cell is None:
            failures.append(f"{path}: no ROWS cell found")
            _emit("FAIL", f"{path.relative_to(REPO_ROOT)}: no ROWS cell", quiet=quiet)
            continue
        rows_here = rows_cell.count('"id":')
        if row_count == -1:
            row_count = rows_here
        elif rows_here != row_count:
            failures.append(
                f"{path}: {rows_here} rows differs from sibling notebook ({row_count})"
            )
            _emit("FAIL", f"{path.relative_to(REPO_ROOT)}: row drift", quiet=quiet)
            continue
        _emit(
            "OK",
            f"{path.relative_to(REPO_ROOT)}: {len(cells)} cells, {rows_here} rows",
            quiet=quiet,
        )
    return failures, row_count


def check_benchmark_module(*, quiet: bool) -> tuple[list[str], int]:
    """Returns (failures, len(DEFAULT_FALLBACK_ROWS))."""
    print("[3/6] duecare.chat.benchmark import + DEFAULT_FALLBACK_ROWS")
    failures: list[str] = []
    try:
        from duecare.chat.benchmark import (
            CORE_CRITERIA,
            CRITERIA_VERSION,
            DEFAULT_FALLBACK_ROWS,
            known_domains,
        )
    except ImportError as exc:
        failures.append(f"import failed: {exc}")
        _emit("FAIL", f"import: {exc}", quiet=quiet)
        return failures, -1
    _emit("OK", f"CRITERIA_VERSION={CRITERIA_VERSION}", quiet=quiet)
    _emit("OK", f"len(CORE_CRITERIA)={len(CORE_CRITERIA)}", quiet=quiet)
    _emit("OK", f"len(DEFAULT_FALLBACK_ROWS)={len(DEFAULT_FALLBACK_ROWS)}", quiet=quiet)
    _emit("OK", f"known_domains()={known_domains()}", quiet=quiet)
    return failures, len(DEFAULT_FALLBACK_ROWS)


def check_selftest(*, quiet: bool) -> list[str]:
    print("[4/6] scripts/selftest_benchmark.py --judge mock")
    failures: list[str] = []
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts/selftest_benchmark.py"),
        "--judge",
        "mock",
    ]
    try:
        out = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120, cwd=str(REPO_ROOT)
        )
    except FileNotFoundError as exc:
        failures.append(f"selftest_benchmark.py not found: {exc}")
        _emit("FAIL", f"selftest_benchmark.py missing: {exc}", quiet=quiet)
        return failures
    except subprocess.TimeoutExpired:
        failures.append("selftest_benchmark.py timed out (>120s)")
        _emit("FAIL", "selftest timeout", quiet=quiet)
        return failures
    if out.returncode != 0:
        failures.append(f"selftest exit {out.returncode}: {out.stdout[-400:]}")
        _emit("FAIL", f"selftest exit {out.returncode}", quiet=quiet)
        if not quiet:
            print(out.stdout[-1000:])
        return failures
    summary_line = next(
        (line for line in out.stdout.splitlines() if line.startswith("summary:")),
        "",
    )
    _emit("OK", summary_line or "selftest exit 0", quiet=quiet)
    return failures


def check_grade_benchmark_endpoint(*, quiet: bool) -> list[str]:
    print("[5/6] /api/grade-benchmark TestClient roundtrip")
    failures: list[str] = []
    try:
        from fastapi.testclient import TestClient
        from duecare.chat.app import create_app
    except ImportError as exc:
        failures.append(f"FastAPI/app import failed: {exc}")
        _emit("FAIL", f"import: {exc}", quiet=quiet)
        return failures
    try:
        app = create_app()
        client = TestClient(app)
        resp = client.post(
            "/api/grade-benchmark",
            json={
                "prompt_text": "What is the legal cap on the placement fee?",
                "response_text": (
                    "Under ILO Convention 181 and DMW rules, recruitment "
                    "agencies must not charge HSWs a placement fee. "
                    "Preserve receipts as evidence and contact the DMW "
                    "hotline if pressured."
                ),
            },
        )
    except Exception as exc:  # noqa: BLE001
        failures.append(f"endpoint call raised: {exc}")
        _emit("FAIL", f"endpoint exception: {exc}", quiet=quiet)
        return failures
    if resp.status_code != 200:
        failures.append(f"endpoint HTTP {resp.status_code}: {resp.text[:200]}")
        _emit("FAIL", f"HTTP {resp.status_code}", quiet=quiet)
        return failures
    body = resp.json()
    required = {
        "row_id",
        "score",
        "passed",
        "deterministic_pct",
        "used_judge",
        "criteria_version",
        "reasons",
    }
    missing = required - set(body.keys())
    if missing:
        failures.append(f"response missing keys: {sorted(missing)}")
        _emit("FAIL", f"missing keys: {sorted(missing)}", quiet=quiet)
        return failures
    if not isinstance(body["score"], (int, float)) or not (0.0 <= body["score"] <= 1.0):
        failures.append(f"score out of range: {body['score']}")
        _emit("FAIL", f"score out of range: {body['score']}", quiet=quiet)
        return failures
    _emit(
        "OK",
        f"endpoint score={body['score']:.2f} passed={body['passed']} "
        f"version={body['criteria_version']}",
        quiet=quiet,
    )
    # Liveness sibling: confirm /api/health also serves with the
    # request-ID middleware applied. A failure here would point at a
    # bad middleware registration that breaks every endpoint.
    try:
        liveness = client.get("/api/health")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"/api/health raised: {exc}")
        _emit("FAIL", f"liveness exception: {exc}", quiet=quiet)
        return failures
    if liveness.status_code != 200:
        failures.append(f"/api/health HTTP {liveness.status_code}")
        _emit("FAIL", f"/api/health HTTP {liveness.status_code}", quiet=quiet)
        return failures
    rid_header = liveness.headers.get("X-Request-ID") or ""
    rid_body = (liveness.json() or {}).get("request_id") or ""
    if not rid_header or rid_header != rid_body:
        failures.append(
            f"/api/health request-id mismatch: header={rid_header!r} body={rid_body!r}"
        )
        _emit("FAIL", "/api/health request-id mismatch", quiet=quiet)
        return failures
    _emit("OK", f"/api/health 200 ok request_id={rid_header}", quiet=quiet)
    return failures


def check_row_count_alignment(
    *,
    quiet: bool,
    notebook_rows: int,
    adapter_rows: int,
) -> list[str]:
    print("[6/6] row-count alignment (adapter vs published notebook)")
    failures: list[str] = []
    if notebook_rows < 0 or adapter_rows < 0:
        _emit("INFO", "skipped (earlier check failed)", quiet=quiet)
        return failures
    if notebook_rows <= 0:
        failures.append("published notebook has 0 rows")
        _emit("FAIL", "0 rows in notebook", quiet=quiet)
        return failures
    if notebook_rows > adapter_rows:
        failures.append(
            f"notebook has {notebook_rows} rows but adapter only exposes "
            f"{adapter_rows} -- rows in the notebook aren't covered by tests"
        )
        _emit("FAIL", f"notebook ({notebook_rows}) > adapter ({adapter_rows})", quiet=quiet)
        return failures
    _emit(
        "OK",
        f"notebook={notebook_rows} rows, adapter={adapter_rows} rows "
        f"(notebook covers {notebook_rows / max(adapter_rows, 1):.0%} of adapter corpus)",
        quiet=quiet,
    )
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--quiet", action="store_true", help="Only print FAIL lines.")
    args = parser.parse_args(argv)

    src_root = REPO_ROOT / "packages" / "duecare-llm-chat" / "src"
    if src_root.exists() and str(src_root) not in sys.path:
        sys.path.insert(0, str(src_root))

    print(f"DueCare benchmark validator")
    print(f"  repo: {REPO_ROOT}")
    print(f"  python: {sys.version.split()[0]}")
    print()

    failures: list[str] = []
    failures += check_kernel_syntax(quiet=args.quiet)
    nb_failures, nb_rows = check_task_notebook(quiet=args.quiet)
    failures += nb_failures
    mod_failures, adapter_rows = check_benchmark_module(quiet=args.quiet)
    failures += mod_failures
    failures += check_selftest(quiet=args.quiet)
    failures += check_grade_benchmark_endpoint(quiet=args.quiet)
    failures += check_row_count_alignment(
        quiet=args.quiet, notebook_rows=nb_rows, adapter_rows=adapter_rows,
    )

    print()
    if failures:
        print(f"FAIL: {len(failures)} check(s) failed:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("OK: all 6 checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
