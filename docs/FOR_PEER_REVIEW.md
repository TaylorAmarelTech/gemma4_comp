# For Judges and Reviewers

This is the current 2026-05-17 verification path for the DueCare Gemma 4
Good Hackathon submission. Older notebook-era material is archived or marked
historical; the active Kaggle path is exactly the two script kernels listed
below.

## Thirty-Second Summary

DueCare is a Gemma 4 harness ecosystem for migrant-worker exploitation risk.
It wraps Gemma 4 with reusable safety layers, knowledge packs, deterministic
tools, sensitive-data handling, evaluation, and report generation. The current proof
focuses on two active surfaces:

| Surface | Purpose |
|---|---|
| `kaggle/01-duecare-exploration-workbench/` | Broad interactive workbench: chat, harness comparison, search, knowledge extraction, bulk review, traces, and activity logs. |
| `kaggle/02-live-demo/` | Focused live demo and video path. |

The active inventory is tracked in [`kaggle/_INDEX.md`](../kaggle/_INDEX.md)
and [`docs/current_kaggle_notebook_state.md`](current_kaggle_notebook_state.md).
A-00 remains available as archived proof material, not an active recording
kernel.

## What To Verify First

1. Open `01-duecare-exploration-workbench` and run the chat/harness comparison
   path. Confirm the default harness uses Persona + GREP + RAG/context + tools,
   with online search/imports only when explicitly enabled.
2. Optional only: open archived `A-00-omni-experiment-workbench` and run the
   preconfigured path for a small prompt count if new proof artifacts are
   needed. Confirm the Activity log shows the numbered pipeline steps,
   prompt/response artifacts, combined rule + LLM grading, and report bundle
   links under `/kaggle/working`.
3. Confirm all local inference model loading goes through
   `Gemma4Runtime.load()` and the Unsloth `FastModel` recipe documented in
   [`docs/model_loading_trace.md`](model_loading_trace.md).

## Current Harness Contract

The authoritative harness docs are:

- [`docs/harness_ecosystem.md`](harness_ecosystem.md) - registered harness
  inventory and broader harness families.
- [`docs/harness_pattern.md`](harness_pattern.md) - module contract and
  active Kaggle integration pattern.
- [`docs/harness_standard_contract.md`](harness_standard_contract.md) -
  universal `HarnessSpec`, model targets, transports, and pack contracts.

The registered harnesses are `chat`, `process`, `extraction`,
`anonymization`, `search_safety`, `post_search_verification`, `search`, and
`import_corpus`. Archived A-00 also uses pipeline-specific harness families for
synthetic data generation, fine-tuning, combined judging, checkpointing, and
report/export bundles.

## Archived A-00 Proof Path

The preconfigured archived A-00 pipeline should:

1. Check/unload current model state.
2. Check disk space and clean if needed.
3. Load the selected Gemma model through the shared runtime.
4. Run prompts without the harness.
5. Run the same prompts with the offline DueCare harness.
6. Generate synthetic SFT rows from harnessed outputs.
7. Optionally fine-tune a LoRA adapter with checkpoint/resume enabled.
8. Run fine-tuned no-harness and fine-tuned harnessed arms when training is enabled.
9. Load the selected judge model or configured external judge.
10. Grade all response sets with combined rule + LLM judging.
11. Write HTML, Markdown, JSON, CSV, SVG, PDF-summary, activity, and evidence ZIP artifacts.

Default offline harness behavior should match the Kernel 01 comparison path:
Persona + GREP + RAG/context + deterministic tools, with internet and import
off for the default proof run.

## Verification Commands

From the repository root:

```powershell
$env:PYTHONPATH='packages/duecare-llm-models/src;packages/duecare-llm-chat/src;packages/duecare-llm-core/src'

python -m py_compile `
  kaggle\_archive\notebooks\A-00-omni-experiment-workbench\kernel.py `
  scripts\generate_notebook_guide.py `
  scripts\kaggle_notebook_utils.py

python -m pytest `
  tests\test_a00_runtime_and_parity_contract.py `
  tests\test_a00_notebook_contract.py `
  tests\test_harness_universal_model_contract.py `
  tests\test_harness_standard_contract.py `
  tests\test_harness_imports.py `
  tests\test_harness_ecosystem_docs.py `
  tests\test_kaggle_notebook_utils.py `
  packages\duecare-llm-chat\tests\test_harness_workbench.py `
  packages\duecare-llm-chat\tests\test_workbench_inventory_integrity.py `
  packages\duecare-llm-models\tests\test_models_package_smoke.py `
  -q --basetemp=.pytest_tmp
```

## What This Submission Does Not Claim

- It does not require archived notebook-era surfaces for the current judge path.
- It does not require paid external judge APIs; Anthropic and Ollama judge
  routes are optional.
- It does not send raw private case material to a public search engine in the
  default proof path.
- It does not treat generated or imported knowledge as automatic truth; human
  review and provenance remain part of the workflow.
