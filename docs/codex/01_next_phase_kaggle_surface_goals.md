# 01 - Next-phase Kaggle surface goals

> Source review date: 2026-05-25. Scope: active root `kaggle/` folders only:
> `01-duecare-exploration-workbench`, `02-live-demo`, and optional benchmark
> folders `03-universal-llm-benchmark` and `04-kaggle-community-benchmark`.

## Current Read

The root Kaggle layout is clean and guarded by
`scripts/validate_main_kaggle_kernels.py`: active submission surfaces are
`01` and `02`; optional benchmarks are the single root `03` and single root
`04-kaggle-community-benchmark`; appendix `A-*` material remains archived.

The source code shows four different product jobs:

| Surface | Product job | Review priority |
|---|---|---|
| `01-duecare-exploration-workbench` | Broad technical workbench: chat, comparison, Bulk File Review, Knowledge Extraction, Search, Templates, Anonymization and Sharing, Status, layer catalogs. | Highest for source cleanup and reviewer trust. |
| `02-live-demo` | Focused recording path: `/start`, `/slides`, `/slides/setup`, cached replay pack, and cross-mounted `/wb-static/*` workbench routes. | Highest for video readiness. |
| `03-universal-llm-benchmark` | Bring-your-own endpoint benchmark with DueCare prompts, target calls, judge/fallback scoring, and JSON/HTML outputs. | Good next proof surface, but optional for primary recording. |
| `04-kaggle-community-benchmark` | Kaggle-native benchmark task shim using `kaggle_benchmarks` when available and local preview otherwise. | Good public comparison surface once registration is stable. |

## Review Findings

- The existing kernel gate protects bootability and root layout, but not page
  asset references. Added `scripts/validate_kaggle_page_sources.py` to close
  that gap.
- Kernel 02 recording pages referenced `/static/styles.css`, but the server
  package ships `/static/style.css`. This is now fixed and pinned in tests.
- Several workbench pages linked `/static/chat.html`, but the package only
  shipped `index.html` as the canonical chat implementation. A compatibility
  `chat.html` redirect now preserves those deep links.
- Bulk File Review honestly states that the current `gemma_case_brief` is not
  a document/page/paragraph/table-row pass. Goal 11 is still the architectural
  fix for hierarchy-level Gemma nodes and edges.
- The benchmark kernels are source-parseable and guarded by the main kernel
  gate, but they need stronger source-level contracts around report schemas,
  multi-target comparison, local-preview fidelity, and public registration flow.

## Next Goal Set

Recommended execution order:

1. Goal 12 - Kernel 01 workbench page polish and page-source regression gate.
2. Goal 13 - Kernel 02 recording-path polish and cached replay verification.
3. Goal 11 - Hierarchical Gemma graph passes for Bulk File Review.
4. Goal 14 - Universal LLM benchmark comparison/report upgrade.
5. Goal 15 - Kaggle Community Benchmark task maturity and registration proof.

This order keeps the primary demo testable before the larger graph architecture
work, then moves the optional benchmark proof surfaces forward.

## Verification Strategy

Run the smallest relevant gate first, then widen:

| Change type | Required checks |
|---|---|
| Any root `kaggle/` or active-kernel docs change | `python scripts/validate_main_kaggle_kernels.py` |
| Any 01/02 HTML, static asset, route link, or benchmark marker change | `py -3.12 scripts/validate_kaggle_page_sources.py` |
| Kernel 01 workflow page changes | `python -m pytest packages/duecare-llm-chat/tests/test_harness_workbench.py -q` plus affected focused tests; Playwright `npm.cmd run test:smoke` from `kaggle/01-duecare-exploration-workbench/tests` when browser deps are installed. |
| Kernel 02 recording pages | `python -m pytest packages/duecare-llm-server/tests/test_slides_surface.py -q` |
| Bulk File Review graph behavior | `python -m pytest packages/duecare-llm-chat/tests/test_process_bulk_review.py -q` |
| Universal/Kaggle benchmark logic | `python -m pytest packages/duecare-llm-chat/tests/test_benchmark.py -q`, `py -3.12 -m py_compile kaggle/03-universal-llm-benchmark/kernel.py kaggle/04-kaggle-community-benchmark/kernel.py` |
| Public docs/links | `python scripts/validate_public_surface.py` |

Known local caveat: this checkout has had a broken global pytest install and
missing hub dependencies in prior runs. If pytest cannot import locally,
record the exact import failure, run the pure-stdlib gates, and avoid claiming
a full test pass.

## Non-goals

- Do not restore appendix `A-*` folders to root `kaggle/`.
- Do not reintroduce extra root `04-*` task snapshots.
- Do not rename published routes, DOM IDs, sample filenames, or kernel folders.
- Do not make the benchmark surfaces part of the primary recording path unless
  Taylor explicitly promotes them.
