# Next Notebook Reuse Audit

Review date: 2026-05-15

Purpose: confirm that notebooks after Kernel 01 reuse package-level contracts
instead of copying endpoint lists, sample names, graph-edge schemas, training
defaults, or UI shell behavior.

## Shared Sources Of Truth

- `duecare.chat.portability`: version floor, required endpoints, required
  samples, knowledge taxonomy count, process phases, graph-edge schema,
  knowledge I/O contract, model-fit profiles, trust-boundary vocabulary, and
  self-audit minimum counts.
- `duecare.chat.experiment_contracts`: harness profiles, `bulk_text_25`,
  `bulk_text_50`, `tiny_lora_smoke`, synthetic generation profiles, upload
  limits, training profiles, and the four-arm comparison matrix.
- `duecare.chat.kernel_shell`: common shell for appendix notebooks. It now
  exposes `GET /api/portability` and `GET /api/experiment-contract` for every
  notebook using `build_minimal_shell`.
- `duecare.chat.app.create_app`: full Workbench app used by Kernel 01 and
  A-10; exposes the Workbench portability endpoint directly.

## Notebook Reuse Status

| Notebook | Reuse path | Status |
|---|---|---|
| `02-live-demo` | Server app plus `reference_portability_contract_payload()`, `/api/portability`, and `/api/experiment-contract` | OK |
| `03-duecare-video-pitch` | `build_minimal_shell` plus video export embeds portability payload | OK |
| `A-00-omni-experiment-workbench` | `build_minimal_shell`, direct portability imports, direct experiment-contract imports, `/api/a00/experiment-contract`, `/api/a00/quantitative/run` | OK |
| `A-01` to `A-09`, `A-11` to `A-24` | `build_minimal_shell`; inherit `/api/portability` and `/api/experiment-contract` from the shell | OK |
| `A-10-runtime-vs-weights-safety-study` | full `duecare.chat.app.create_app`; inherits Workbench `/api/portability` and `/api/experiment-contract` from the app | OK |
| `A-07-bench-and-tune` | `build_minimal_shell` plus direct `training_profile_map()` and `upload_limit_map()` from `experiment_contracts` | OK |

## What Must Not Be Reintroduced

- Do not restate `DUECARE_REQUIRED_APP_ENDPOINTS`,
  `DUECARE_REQUIRED_SAMPLE_FILES`, or `DUECARE_REQUIRED_KO_TYPES` inside
  downstream notebooks.
- Do not hardcode `bulk_text_25`, LoRA smoke parameters, upload limits, or
  training batch settings outside `duecare.chat.experiment_contracts`.
- Do not add appendix-only artifact download handling; use
  `build_minimal_shell` so nested artifact paths and standard logs stay
  consistent.
- Do not use raw case-bundle language where an import expects reviewed
  `knowledge_files.zip`.

## Regression Gate

`packages/duecare-llm-chat/tests/test_kaggle_kernel01_portability.py` now
checks that every next notebook uses one of the shared runtime surfaces:

- `build_minimal_shell`
- full `duecare.chat.app.create_app`
- server `create_app`
- explicit `/api/portability` or `reference_portability_contract_payload`

The same test also blocks reintroduced duplicate endpoint/sample/taxonomy
lists in downstream notebooks.

## Path And Endpoint Simulation Gate

The local path audit now covers all active kernels:

- `01-duecare-exploration-workbench`
- `02-live-demo`
- `03-duecare-video-pitch`
- `A-00` through `A-24`

For every kernel, the gate verifies:

- UTF-8 text without a byte-order mark, so kernels parse cleanly when pasted or
  uploaded as notebook cells.
- `ast.parse(...)` succeeds locally without executing model-load code.
- No local workstation paths such as `C:\...`, `OneDrive`, `/Users/...`,
  `/home/...`, or `/mnt/...` leak into the notebook.
- A README exists next to each active kernel.
- Each active kernel uses one shared runtime surface: minimal shell, full chat
  app, server app, or explicit portability contract.

`packages/duecare-llm-chat/tests/test_workbench_inventory_integrity.py` also
simulates the reusable endpoint paths without opening a tunnel:

- full Workbench static pages and core APIs serve locally;
- `case_files_media_rich_sample.zip` serves from `/static/samples/...`;
- minimal-shell `/`, `/summary`, `/api/version`, `/api/portability`,
  `/api/experiment-contract`, `/api/model-info`, `/api/brand`, and activity-log
  endpoints serve;
- nested artifacts resolve under `/artifact/<relative/path>`;
- artifact path traversal is blocked.
