# Kernel 01 Portability Audit

Review date: 2026-05-15

Purpose: make `01-duecare-exploration-workbench` the reusable source of truth for the next notebooks: `02-live-demo`, `03-duecare-video-pitch`, `A-00-omni-experiment-workbench`, and appendix kernels.

Companion audit: `NEXT_NOTEBOOK_REUSE_AUDIT.md` records how each next
notebook consumes these contracts.

## Reusable Contract

Kernel 01 should be reused as a package/runtime contract, not copied page-by-page.

Reusable package module:

- `duecare.chat.portability`
- `portability_contract_payload(...)`
- `verify_app_contract(...)`
- `REQUIRED_APP_ENDPOINTS`
- `REQUIRED_SAMPLE_FILES`
- `REUSABLE_PRIMITIVES`
- `MODEL_VARIANT_PROFILES`
- `PROCESS_PHASES`
- `GRAPH_EDGE_CONTRACT`
- `KNOWLEDGE_IO_CONTRACTS`
- `CORE_NOTEBOOKS`
- `SELF_AUDIT_MINIMUM_COUNTS`

Required package:

- `duecare-llm-chat >= 0.17.0`
- `duecare-llm-core` and `duecare-llm-models` compatible with the installed chat package

Required runtime endpoints:

- `GET /api/version`
- `GET /api/brand`
- `GET /api/health-check`
- `GET /api/harnesses`
- `GET /api/portability`
- `GET /api/experiment-contract`
- `GET /api/audit/workbench-inventory`
- `GET /api/knowledge/taxonomy`
- `GET /api/knowledge/type-catalog`
- `POST /api/knowledge/import`
- `GET /api/knowledge/export`
- `POST /api/process/batch/start`
- `GET /api/process/batch/status/{job_id}`
- `POST /api/search/sanitize`
- `POST /api/anonymize`

Required bundled sample assets:

- `sample_manifest.json`
- `case_files_media_rich_sample.zip`
- `knowledge_files_sample.zip`
- `knowledge_source_examples_sample.zip`
- `search_intake_examples_sample.zip`
- `prompt_eval_training_seed_sample.zip`

Required knowledge taxonomy:

- 7 branches
- 28 leaf types
- `GET /api/knowledge/type-catalog` must describe each leaf's purpose, required keys, useful optional keys, and example content.

Kernel 01 now imports these constants from `duecare.chat.portability` during
its self-audit and runtime portability check, so the notebook no longer
maintains a second route/sample/taxonomy list beside the package contract.
Stale wheels fail before the UI opens.

## Reusable Primitives Worth Carrying Forward

Use these as shared modules or mirrored contracts in the next notebooks:

- **Workbench inventory endpoint**: one JSON source for pages, samples, import/export routes, taxonomy counts, and gaps.
- **Knowledge type catalog**: the canonical map of every knowledge leaf and subtype.
- **Sample manifest**: separates source case bundles from knowledge files, search examples, and training/eval seeds.
- **Harness surface contracts**: each harness declares consumed inputs, emitted outputs, model role, routes, pages, and examples.
- **Async job contract**: long processing flows should use `start -> status -> result` rather than a single request that can hit Cloudflare 524.
- **Graph edge schema**: every edge should carry source file, page/chunk, extractor, confidence, quote/bbox where available, and `local_only` provenance.
- **Model fit profile**: shared warnings for small vs large Gemma 4 variants, especially OCR/vision, graph-edge generation, and LLM grading.
- **Process phase contract**: upload, stage, inventory, parse, OCR/layout, deterministic extraction, Gemma edge pass, and reviewer verification.
- **Core notebook roster**: one map for the roles of 01, 02, 03, and A-00.
- **Trust-boundary vocabulary**: consistently distinguish source case bundles, knowledge files, redacted submissions, and hub-bound aggregate facts.
- **Activity log primitive**: every workflow writes the same bottom activity log entries for API calls, status changes, errors, and exports.
- **Import/export envelope contract**: knowledge files are ZIPs of reviewed KnowledgeObject envelopes plus README/metadata, not raw case folders.
- **Quantitative experiment contract**: `duecare.chat.experiment_contracts`
  centralizes harness profiles, bulk comparison defaults, synthetic generation
  profiles, tiny LoRA smoke settings, upload limits, and the four-arm
  stock/fine-tuned/harness comparison matrix.
- **Minimal-shell contract endpoints**: `duecare.chat.kernel_shell` now exposes
  `GET /api/portability` and `GET /api/experiment-contract` by default, so
  appendix notebooks that use the shared shell inherit the same machine-readable
  contracts without copying endpoint lists or training defaults.

## Notebook-Specific Incorporation

### 02 Live Demo

Reuse the Kernel 01 package and endpoint contract, but keep the UI focused. It should call or cite:

- `/api/harnesses` for the short harness map
- `/api/audit/workbench-inventory` for live counts
- `/api/knowledge/type-catalog` for knowledge-object language
- `case_files_media_rich_sample.zip` for the unified PH-HK demo story
- `prompt_eval_training_seed_sample.zip` for the comparison/evaluation story

Recommended design: scripted panels over the same primitives, not a second bespoke harness.

### 03 Video Pitch

Keep zero-inference if needed, but align screenshots and language with Kernel 01:

- package version `0.17.0`
- same five audience lanes
- same trust-boundary terms
- same source bundle vs knowledge file distinction
- same warning that media/OCR/Gemma-vision quality depends on model size and local wiring

### A-00 Omni Experiment Workbench

A-00 should import the Kernel 01 taxonomy and sample manifest where possible:

- consume `knowledge_files_sample.zip` as importable knowledge
- consume `prompt_eval_training_seed_sample.zip` for synthetic SFT/preference seeds
- reuse the graph-edge schema for generated synthetic cases
- keep fine-tune smoke tests tiny, local, and clearly separated from production claims

### Appendix Notebooks

Appendix kernels should now use `os.environ.get("DUECARE_VERSION", "0.17.0")`
instead of hardcoded `0.1.0` pins. Before recording or publishing, verify:

- each appendix inherits the `0.17.0` default or an explicit override, and
- any intentionally old appendix is marked legacy/illustrative while the three core notebooks plus A-00 remain the authoritative runtime.

## Known Portability Risks

- Local fallback folders now include `duecare_llm_chat-0.17.0-py3-none-any.whl`.
- Legacy `duecare_llm_chat-0.16.0` fallback wheels may remain beside the refreshed wheel until the Kaggle dataset is republished; install code sorts local wheels so the refreshed chat wheel wins.
- Dataset metadata for Kernel 01 and Kernel 02 has been updated locally, but the Kaggle datasets still need to be versioned/published from these folders.
- If judges run against an old uploaded Kaggle dataset instead of the current repository/fallback bundle, new endpoints such as `/api/portability`, `/api/audit/workbench-inventory`, and `/api/knowledge/type-catalog` may be missing.

Required before final video:

1. Publish the refreshed `duecare-llm-chat 0.17.0` wheel datasets to Kaggle.
2. Refresh Kaggle wheel dataset metadata from the local `wheels/dataset-metadata.json` files.
3. Re-run Kernel 01 and confirm the portability contract prints OK.
4. Run 02, 03, A-00 using the same version floor.

## Monday Polish Queue

Remaining items are now mostly validation and recording readiness rather than
new architecture:

- Run A-00 `bulk_text_25`: stock Gemma 4 E2B/E4B with `none` vs `chat_full`
  over 25 prompts, then export the HTML/Markdown/JSON report.
- Run A-00 `tiny_lora_smoke`: generate 24 rubric-polished SFT/DPO rows, create
  the LoRA training job, optionally execute on GPU, and compare stock,
  stock+harness, fine-tuned, and fine-tuned+harness using the same prompt set.
- Re-run the full Kernel 01 UI path with `case_files_media_rich_sample.zip`:
  Compare, Process, Knowledge, Search, Share, Status, and UI Audit.
- Record exact load/process timings for E2B and E4B so the video can describe
  realistic runtimes without overclaiming.
- Confirm Knowledge Extraction exports a `knowledge_files.zip` bundle that
  imports cleanly into Anonymization & Sharing.
- Confirm Bulk File Review uses async job polling for larger bundles and logs
  upload, staging, inventory, OCR/layout, deterministic extraction, Gemma edge
  pass, and reviewer verification phases.
- Confirm all pages open without stale model-selector overlay layout issues.
- Publish the refreshed wheel datasets, then run a clean Kaggle session against
  those published artifacts.
- Keep external claims conservative until Monday benchmark/comparison/fine-tune
  runs produce final numbers.
