# Repository Layout

Current as of 2026-05-25.

| Path | Purpose | Status |
|---|---|---|
| [`apps/duecare-ai.com/`](../apps/duecare-ai.com/) | Public coordination hub and website surface. CPU-only; no local Gemma inference. | Live |
| [`packages/`](../packages/) | Python packages under the `duecare` namespace. Source of truth for reusable chat, model, harness, server, and training code. | Live |
| [`packages/duecare-llm-chat/`](../packages/duecare-llm-chat/) | Main FastAPI chat/harness package, static UI, shared GREP/RAG/tools, harness registry, and Gemma runtime integration. | Live |
| [`packages/duecare-llm-models/`](../packages/duecare-llm-models/) | Model adapter package used by local and optional external model paths. | Live |
| [`kaggle/`](../kaggle/) | Active Kaggle submission path plus archived notebook-era material. Source of truth: [`kaggle/_INDEX.md`](../kaggle/_INDEX.md). | Live |
| [`kaggle/01-duecare-exploration-workbench/`](../kaggle/01-duecare-exploration-workbench/) | Broad interactive workbench: chat, harness comparison, search, extraction, traces, and knowledge flows. | Active |
| [`kaggle/02-live-demo/`](../kaggle/02-live-demo/) | Focused demo/video path. | Active |
| [`kaggle/A-00-omni-experiment-workbench/`](../kaggle/A-00-omni-experiment-workbench/) | Active quantitative proof path: baseline, harness, synthetic rows, optional LoRA, judging, and report exports. | Active |
| [`kaggle/03-universal-llm-benchmark/`](../kaggle/03-universal-llm-benchmark/) | Optional endpoint-comparison kernel for arbitrary API targets, DueCare prompt/rubric cues, and Claude Opus judging. | Optional |
| [`kaggle/04-kaggle-community-benchmark/`](../kaggle/04-kaggle-community-benchmark/) | Optional Kaggle Community Benchmark surface using `kaggle_benchmarks` and Kaggle model proxy calls. | Optional |
| [`kaggle/_archive/notebooks/`](../kaggle/_archive/notebooks/) | Retired A-series, video-pitch, and task-notebook-era surfaces. | Historical |
| [`docs/`](../docs/) | Current docs plus archived historical docs. Main reviewer entry: [`FOR_PEER_REVIEW.md`](FOR_PEER_REVIEW.md). | Live |
| [`docs/_archive/`](../docs/_archive/) | Historical docs retained for provenance. | Historical |
| [`tests/`](../tests/) | Cross-package contract and documentation tests. | Live |

## Current Entry Points

- Reviewer path: [`docs/FOR_PEER_REVIEW.md`](FOR_PEER_REVIEW.md)
- Manual checklist: [`docs/USER_TODO.md`](USER_TODO.md)
- Current status: [`docs/readiness_dashboard.md`](readiness_dashboard.md)
- User path chooser: [`docs/user_paths.md`](user_paths.md)
- Active Kaggle inventory: [`docs/current_kaggle_notebook_state.md`](current_kaggle_notebook_state.md)
- Model loading: [`docs/model_loading_trace.md`](model_loading_trace.md)
- Harness inventory: [`docs/harness_ecosystem.md`](harness_ecosystem.md)
- Root file policy: [`ROOT_FILES.md`](../ROOT_FILES.md)
- File purpose policy: [`docs/FILE_PURPOSE_GUIDE.md`](FILE_PURPOSE_GUIDE.md)
- Kaggle Community Benchmark notes: [`docs/KAGGLE_COMMUNITY_BENCHMARK.md`](KAGGLE_COMMUNITY_BENCHMARK.md)
- Screenshot audit checklist: [`docs/SCREENSHOT_AUDIT.md`](SCREENSHOT_AUDIT.md)

## Archival Rule

If a doc primarily describes the retired appendix ladder, old publish status,
old score projections, or A-01 through A-24 as the active submission path, it
belongs under `docs/_archive/2026-05-16-legacy-notebook-era/` unless it has been
rewritten around the current active Kaggle scope.

Root `kaggle/` must not contain appendix `A-*` folders other than the active
`A-00-omni-experiment-workbench`, and the only root `04-*` folder should be
`04-kaggle-community-benchmark`.
