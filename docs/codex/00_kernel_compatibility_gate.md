# 00 - Kernel compatibility gate

> Created 2026-05-24. Applies to every Codex goal that touches packages, static workbench pages, routes, sample artifacts, Kaggle publishing behavior, or docs that instruct agents to commit/push goal work.

## Scope

This gate protects the five non-archived Kaggle `kernel.py` files and their Kaggle metadata that a judge or reviewer can still run:

| Tier | Path | Why it matters |
|---|---|---|
| Active | `kaggle/01-duecare-exploration-workbench/kernel.py` | Main DueCare App / reviewer workbench |
| Active | `kaggle/02-live-demo/kernel.py` | Focused recording and live demo path |
| Active | `kaggle/A-00-omni-experiment-workbench/kernel.py` | Fine-tuning, evaluation, and experiment control plane |
| Optional | `kaggle/03-universal-llm-benchmark/kernel.py` | External endpoint benchmark |
| Optional | `kaggle/04-kaggle-community-benchmark/kernel.py` | Kaggle Community Benchmark task flow |

Appendix notebooks, archived notebooks, and legacy notebook-era folders are intentionally out of scope for this gate unless Taylor explicitly asks to restore or migrate them.

## Required command

Run this before committing each goal:

```bash
python scripts/validate_main_kaggle_kernels.py
```

This is a static, pure-stdlib check. It does not import DueCare packages, launch FastAPI, install dependencies, download models, or start cloudflared. It verifies that the main kernels:

- still exist in their published folders,
- parse as Python,
- are UTF-8 readable,
- do not contain merge-conflict markers,
- keep the Kaggle-facing boot tokens that make the notebook runnable in Kaggle,
- keep `kernel-metadata.json` publish settings aligned with the intended Kaggle slug, `kernel.py` code file, script kernel type, Internet setting, and GPU setting.

## When the gate fails

If this gate fails after a goal change:

1. Fix the goal implementation or docs change.
2. Rerun `python scripts/validate_main_kaggle_kernels.py`.
3. Do not commit or push the goal until the gate is green, unless the failure is a pre-existing issue and Taylor explicitly accepts that risk.

If the goal intentionally changes a main kernel boot path, update `scripts/validate_main_kaggle_kernels.py` in the same commit so the gate reflects the new public contract.
