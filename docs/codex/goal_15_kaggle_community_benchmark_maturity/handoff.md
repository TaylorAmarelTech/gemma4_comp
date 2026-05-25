# Goal 15 - Kaggle Community Benchmark task maturity

> Status: **DONE 2026-05-25 (`2adfa60`)**. Created 2026-05-25 after reviewing
> `kaggle/04-kaggle-community-benchmark/kernel.py`.

## 1. Goal

Make the Kaggle Community Benchmark surface easier to register, preview, and
trust as a public benchmark task.

## 2. Why it matters

The optional `04` kernel is the path for Kaggle-native model proxy runs and
leaderboard-style comparison. It should make the task definition, local preview
mode, row coverage, assertion bundle, and registration status obvious.

## 3. Current state

- The kernel imports shared `duecare.chat.benchmark` modules when available.
- It falls back to embedded rows and a local preview report when
  `kaggle_benchmarks` is unavailable.
- It defines a row-level task and aggregate
  `duecare_migrant_worker_safety_benchmark` task.
- README documents the manual Kaggle task registration caveat.

## 4. Target state

- Local preview report clearly distinguishes "no model call" from benchmark
  proxy execution.
- Report schema includes row coverage by category/difficulty/corridor, scoring
  policy, assertion count, judge availability, and task registration notes.
- The task row corpus and fallback rows stay synchronized with
  `duecare.chat.benchmark.kbench_adapter`.
- README and `COVERAGE.md` reflect the current root `04` status without
  appendix/task-snapshot confusion.

## 5. Files to read first

1. `kaggle/04-kaggle-community-benchmark/kernel.py`
2. `kaggle/04-kaggle-community-benchmark/README.md`
3. `kaggle/04-kaggle-community-benchmark/COVERAGE.md`
4. `packages/duecare-llm-chat/src/duecare/chat/benchmark/`
5. `packages/duecare-llm-chat/tests/test_benchmark.py`

## 6. Files to modify

Keep the root `04-kaggle-community-benchmark` folder as the only active `04-*`
folder. Do not move task snapshots back into root.

## 7. Files to create

Optional: a stdlib local-preview validator that reads the generated report and
checks schema/coverage without importing `kaggle_benchmarks`.

## 8. Acceptance criteria

1. Local preview mode writes a valid report and an operator-readable README.
2. `REPORT_SCHEMA` is bumped only when the report shape changes.
3. Row coverage summary proves fee-limit and corridor probes are present.
4. kbench assertions remain capped at six per row.
5. Registration instructions identify what is manual, what is automated, and
   what evidence should be linked only after a successful Kaggle run.

## 9. Do-not-break checklist

- Do not require `kaggle_benchmarks` for local preview.
- Do not call external models during local tests.
- Do not add a second root `04-*` folder.
- Do not duplicate shared criteria or fallback rows unless the kernel fallback
  path requires a deliberate embedded copy.

## 10. Verification commands

```bash
py -3.12 -m py_compile kaggle/04-kaggle-community-benchmark/kernel.py
py -3.12 scripts/validate_kaggle_page_sources.py
python scripts/validate_main_kaggle_kernels.py
python -m pytest packages/duecare-llm-chat/tests/test_benchmark.py -q
```

## 11. The Codex prompt

```
Improve the root 04 Kaggle Community Benchmark surface from source. Keep local
preview dependency-free, keep kbench execution available when Kaggle wires
kaggle_benchmarks, strengthen report schema/coverage/registration guidance, and
verify that fallback rows stay aligned with duecare.chat.benchmark. Do not add
extra root 04-* folders. Run py_compile, validate_kaggle_page_sources, and the
main-kernel gate.
```

## 12. Out of scope

- Publishing or registering the benchmark through a live Kaggle browser.
- Rewriting the Universal LLM Benchmark, which is Goal 14.
