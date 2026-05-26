# 00 - Kernel compatibility gate

> Created 2026-05-24. Applies to every Codex goal that touches packages, static workbench pages, routes, sample artifacts, Kaggle publishing behavior, or docs that instruct agents to commit/push goal work.

## Scope

This gate protects the Kaggle root layout, the active Kaggle `kernel.py`
files, and the two optional benchmark `kernel.py` files that a judge or
reviewer can still run:

| Tier | Path | Why it matters |
|---|---|---|
| Active | `kaggle/01-duecare-exploration-workbench/kernel.py` | Main DueCare App / reviewer workbench |
| Active | `kaggle/02-live-demo/kernel.py` | Focused recording and live demo path |
| Active | `kaggle/A-00-omni-experiment-workbench/kernel.py` | Quantitative proof, training/evaluation, and report path |
| Optional | `kaggle/03-universal-llm-benchmark/kernel.py` | External endpoint benchmark |
| Optional | `kaggle/04-kaggle-community-benchmark/kernel.py` | Kaggle Community Benchmark task flow |

Appendix notebooks, archived notebooks, and legacy notebook-era folders are
intentionally out of scope for kernel compatibility unless Taylor explicitly
asks to restore or migrate them. The layout check still fails if appendix
`A-*` folders other than the active `A-00-omni-experiment-workbench`, or extra
`04-*` snapshots, are reintroduced at the root.

## Required command

Run this before committing each goal:

```bash
python scripts/validate_main_kaggle_kernels.py
```

This is a static, pure-stdlib check. It does not import DueCare packages,
launch FastAPI, install dependencies, download models, or start cloudflared. It
verifies that the Kaggle root layout and main kernels:

- keep appendix `A-*` other than active `A-00`, and extra `04-*` task snapshots,
  out of root `kaggle/`,
- still exist in their published folders,
- parse as Python,
- are UTF-8 readable,
- do not contain merge-conflict markers,
- keep the Kaggle-facing boot tokens that make the notebook runnable in Kaggle,
- keep `kernel-metadata.json` publish settings aligned with the intended Kaggle slug, `kernel.py` code file, script kernel type, Internet setting, and GPU setting.

For source changes to the Kernel 01/02 HTML pages or the optional benchmark
kernels, run the companion page-source gate as well:

```bash
py -3.12 scripts/validate_kaggle_page_sources.py
```

That gate checks `/static/*` and `/wb-static/*` asset references, Kernel 02
recording-page markers, primary Kernel 01 workbench markers, and benchmark
kernel entrypoint markers without importing DueCare packages.

## When the gate fails

If this gate fails after a goal change:

1. Fix the goal implementation or docs change.
2. Rerun `python scripts/validate_main_kaggle_kernels.py`.
3. Do not commit or push the goal until the gate is green, unless the failure is a pre-existing issue and Taylor explicitly accepts that risk.

If the goal intentionally changes a main kernel boot path, update `scripts/validate_main_kaggle_kernels.py` in the same commit so the gate reflects the new public contract.
