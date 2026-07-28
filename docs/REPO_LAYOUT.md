# Repository Layout

Current as of 2026-07-28.

| Path | Purpose | Status |
|---|---|---|
| [`apps/duecare-ai.com/`](../apps/duecare-ai.com/) | Public coordination hub and website surface. CPU-only; no local Gemma inference. | Live |
| [`packages/`](../packages/) | Python packages under the `duecare` namespace. Source of truth for reusable chat, model, harness, server, and training code. | Live |
| [`packages/duecare-llm-chat/`](../packages/duecare-llm-chat/) | Main FastAPI chat/harness package, static UI, shared GREP/RAG/tools, harness registry, and Gemma runtime integration. | Live |
| [`packages/duecare-llm-models/`](../packages/duecare-llm-models/) | Model adapter package used by local and optional external model paths. | Live |
| [`kaggle/`](../kaggle/) | Active Kaggle submission path plus archived notebook-era material. Source of truth: [`kaggle/_INDEX.md`](../kaggle/_INDEX.md). | Live |
| [`kaggle/01-duecare-exploration-workbench/`](../kaggle/01-duecare-exploration-workbench/) | Broad interactive workbench: chat, harness comparison, search, extraction, traces, and knowledge flows. | Active |
| [`kaggle/02-live-demo/`](../kaggle/02-live-demo/) | Focused demo/video path. | Active |
| [`kaggle/A-00-omni-experiment-workbench/`](../kaggle/A-00-omni-experiment-workbench/) | Active quantitative proof source: baseline, harness, candidate rows, guarded SFT&rarr;DPO, judging, and report exports. The public Kaggle copy attaches the proof dataset; its latest run is canceled and is not completion evidence. | Active source; rerun only for funded proof |
| [`kaggle/shared-datasets/training-data/`](../kaggle/shared-datasets/training-data/) | Documentation-only contract and placeholder metadata for a future full advanced SFT/preference Kaggle Dataset; contains no rows or active `dataset-metadata.json`. The separate combined proof dataset, exact-row SFT/preference views, and CPU companion notebooks are indexed in `kaggle/_INDEX.md`. | Template only; public proofs are separate |
| [`kaggle/03-universal-llm-benchmark/`](../kaggle/03-universal-llm-benchmark/) | Optional endpoint-comparison kernel for arbitrary API targets, DueCare prompt/rubric cues, and Claude Opus judging. | Optional |
| [`kaggle/04-kaggle-community-benchmark/`](../kaggle/04-kaggle-community-benchmark/) | Optional Kaggle Community Benchmark surface using `kaggle_benchmarks` and Kaggle model proxy calls. | Optional |
| [`kaggle/_archive/notebooks/`](../kaggle/_archive/notebooks/) | Retired A-series, video-pitch, and task-notebook-era surfaces. | Historical |
| [`docs/`](index.md) | Current docs plus archived historical docs. Main reviewer entry: [`FOR_PEER_REVIEW.md`](FOR_PEER_REVIEW.md). | Live |
| [`docs/CLAUDE_CODE_HANDOFF.md`](CLAUDE_CODE_HANDOFF.md) | Durable Claude Code and coding-agent pickup: current closeout truth, live-service ownership, recent receipts, safety boundary, and exact next work. | Live |
| [`docs/training_and_finetuning.md`](training_and_finetuning.md) | Public, executable guide to training-data export, local Ollama candidate generation, lineage-safe SFT/DPO preparation, immutable Gemma 4 revisions, Kaggle A-00 execution, and four-arm evaluation. | Live |
| [`docs/research/`](https://github.com/TaylorAmarelTech/gemma4_comp/tree/master/docs/research) | Public research evidence, methods, and status reports. The architecture and publication references are [`evidence_grounded_synthetic_training_blueprint.md`](research/evidence_grounded_synthetic_training_blueprint.md) and [`training_dataset_publication_and_safety_practices.md`](research/training_dataset_publication_and_safety_practices.md); evaluation evidence includes [`training_methodology.md`](research/training_methodology.md), [`training_regimes_and_systems.md`](research/training_regimes_and_systems.md), and [`four_arm_eval.md`](research/four_arm_eval.md), the pending stock/trained by harness-off/on status report. | Live |
| [`docs/entity_intelligence_pipeline.md`](entity_intelligence_pipeline.md) | Canonical map of the propose-only entity-intelligence pipeline: 12 connectors in `scripts/`, the 34-registry cascade in `configs/duecare/research_monitor/`, the 1,111-source + 532-org catalogs, the relationship-edge schema, and the licence ledger. | Live |
| [`scripts/`](../scripts/) + [`configs/duecare/research_monitor/`](../configs/duecare/research_monitor/) | Operator research and training tooling: entity connectors, the config-driven registry resolvers (`registry_specs.yaml`), the licensed-entity / support-org catalogs, guarded candidate-data helpers such as `ollama_adversarial_flywheel.py`, and the approved-release companion builder `build_kaggle_interim_collection.py`. Propose-only outputs stage to gitignored `reports/` until release gates pass. | Live |
| [`configs/duecare/benchmarks/domains/`](../configs/duecare/benchmarks/domains/) | Propose-only cross-domain benchmark registry, synthetic seed packs, and optional grounding manifests, including the developing-country worker-protections sister-benchmark seed. | Live |
| [`configs/duecare/benchmarks/sister_projects/`](../configs/duecare/benchmarks/sister_projects/) | Propose-only sister-project charters for source-gated benchmark programs that sit above domain seeds and curation chains. | Live |
| [`docs/_archive/`](https://github.com/TaylorAmarelTech/gemma4_comp/tree/master/docs/_archive) | Historical docs retained for provenance. | Historical |
| [`tests/`](../tests/) | Cross-package contract and documentation tests. | Live |

## Current Entry Points

- Reviewer path: [`docs/FOR_PEER_REVIEW.md`](FOR_PEER_REVIEW.md)
- Manual checklist: [`docs/USER_TODO.md`](USER_TODO.md)
- Claude Code pickup: [`docs/CLAUDE_CODE_HANDOFF.md`](CLAUDE_CODE_HANDOFF.md)
- Canonical deferred work: [`docs/DEFERRED_WORK.md`](DEFERRED_WORK.md)
- Dated closeout decisions: [`docs/CLOSEOUT_RESOLUTIONS_2026_07_28.md`](CLOSEOUT_RESOLUTIONS_2026_07_28.md)
- Current status: [`docs/readiness_dashboard.md`](readiness_dashboard.md)
- User path chooser: [`docs/user_paths.md`](user_paths.md)
- Active Kaggle inventory: [`docs/current_kaggle_notebook_state.md`](current_kaggle_notebook_state.md)
- Model loading: [`docs/model_loading_trace.md`](model_loading_trace.md)
- Harness inventory: [`docs/harness_ecosystem.md`](harness_ecosystem.md)
- Entity-intelligence pipeline: [`docs/entity_intelligence_pipeline.md`](entity_intelligence_pipeline.md)
- Evidence-grounded training blueprint: [`docs/research/evidence_grounded_synthetic_training_blueprint.md`](research/evidence_grounded_synthetic_training_blueprint.md)
- Training-dataset publication practices: [`docs/research/training_dataset_publication_and_safety_practices.md`](research/training_dataset_publication_and_safety_practices.md)
- Cross-domain domain registry: [`docs/cross_domain_port.md`](cross_domain_port.md)
- Developing-country worker protections seed: [`docs/research/developing_country_worker_protections_benchmark.md`](research/developing_country_worker_protections_benchmark.md)
- Regulatory miss pattern sister-benchmark plan: [`docs/research/regulatory_miss_pattern_benchmark.md`](research/regulatory_miss_pattern_benchmark.md)
- Global protections regulatory sister-project charter: [`docs/research/global_protections_regulatory_benchmark.md`](research/global_protections_regulatory_benchmark.md)
- Global protections project-plan builder: [`scripts/build_global_protections_project_plan.py`](../scripts/build_global_protections_project_plan.py)
- Global protections project-plan validator: [`scripts/validate_global_protections_project_plan.py`](../scripts/validate_global_protections_project_plan.py)
- Global protections jurisdiction-pack matrix builder: [`scripts/build_global_protections_jurisdiction_pack_matrix.py`](../scripts/build_global_protections_jurisdiction_pack_matrix.py)
- Global protections jurisdiction-pack matrix validator: [`scripts/validate_global_protections_jurisdiction_pack_matrix.py`](../scripts/validate_global_protections_jurisdiction_pack_matrix.py)
- Global protections source-channel matrix builder: [`scripts/build_global_protections_source_channel_matrix.py`](../scripts/build_global_protections_source_channel_matrix.py)
- Global protections source-channel matrix validator: [`scripts/validate_global_protections_source_channel_matrix.py`](../scripts/validate_global_protections_source_channel_matrix.py)
- Global protections source-channel review-packet builder: [`scripts/build_global_protections_source_channel_review_packet.py`](../scripts/build_global_protections_source_channel_review_packet.py)
- Global protections source-channel review-packet validator: [`scripts/validate_global_protections_source_channel_review_packet.py`](../scripts/validate_global_protections_source_channel_review_packet.py)
- Global protections benchmark-blueprint builder: [`scripts/build_global_protections_benchmark_blueprint.py`](../scripts/build_global_protections_benchmark_blueprint.py)
- Global protections benchmark-blueprint validator: [`scripts/validate_global_protections_benchmark_blueprint.py`](../scripts/validate_global_protections_benchmark_blueprint.py)
- Global protections evaluation-contract builder: [`scripts/build_global_protections_eval_contract.py`](../scripts/build_global_protections_eval_contract.py)
- Global protections evaluation-contract validator: [`scripts/validate_global_protections_eval_contract.py`](../scripts/validate_global_protections_eval_contract.py)
- Global protections diagnostic-run-plan builder: [`scripts/build_global_protections_diagnostic_run_plan.py`](../scripts/build_global_protections_diagnostic_run_plan.py)
- Global protections diagnostic-run-plan validator: [`scripts/validate_global_protections_diagnostic_run_plan.py`](../scripts/validate_global_protections_diagnostic_run_plan.py)
- Global protections judge-calibration-plan builder: [`scripts/build_global_protections_judge_calibration_plan.py`](../scripts/build_global_protections_judge_calibration_plan.py)
- Global protections judge-calibration-plan validator: [`scripts/validate_global_protections_judge_calibration_plan.py`](../scripts/validate_global_protections_judge_calibration_plan.py)
- Global protections transition-gate builder: [`scripts/build_global_protections_transition_gate.py`](../scripts/build_global_protections_transition_gate.py)
- Global protections transition-gate validator: [`scripts/validate_global_protections_transition_gate.py`](../scripts/validate_global_protections_transition_gate.py)
- Global protections readiness-bundle builder: [`scripts/build_global_protections_readiness_bundle.py`](../scripts/build_global_protections_readiness_bundle.py)
- Global protections readiness-bundle validator: [`scripts/validate_global_protections_readiness_bundle.py`](../scripts/validate_global_protections_readiness_bundle.py)
- Global protections next-actions builder: [`scripts/build_global_protections_next_actions.py`](../scripts/build_global_protections_next_actions.py)
- Global protections next-actions validator: [`scripts/validate_global_protections_next_actions.py`](../scripts/validate_global_protections_next_actions.py)
- Global protections curator-sprint builder: [`scripts/build_global_protections_curator_sprint.py`](../scripts/build_global_protections_curator_sprint.py)
- Global protections curation-bundle builder: [`scripts/build_global_protections_curation_bundle.py`](../scripts/build_global_protections_curation_bundle.py)
- Global protections curation-bundle validator: [`scripts/validate_global_protections_curation_bundle.py`](../scripts/validate_global_protections_curation_bundle.py)
- Global protections saved-artifact validation suite: [`scripts/validate_global_protections_saved_artifacts.py`](../scripts/validate_global_protections_saved_artifacts.py)
- Domain grounding manifest validator: [`scripts/domain_grounding.py`](../scripts/domain_grounding.py)
- Domain source-object curation queue builder: [`scripts/build_domain_grounding_queue.py`](../scripts/build_domain_grounding_queue.py)
- Domain source-research handoff builder: [`scripts/build_domain_source_research_plan.py`](../scripts/build_domain_source_research_plan.py)
- Domain source-coverage matrix builder: [`scripts/build_domain_source_coverage_matrix.py`](../scripts/build_domain_source_coverage_matrix.py)
- Domain source-review intake builder: [`scripts/build_domain_source_review_packet.py`](../scripts/build_domain_source_review_packet.py)
- Domain source-review sprint builder: [`scripts/build_domain_source_review_sprint.py`](../scripts/build_domain_source_review_sprint.py)
- Domain source-review ledger builder: [`scripts/build_domain_source_review_ledger.py`](../scripts/build_domain_source_review_ledger.py)
- Domain source-review validation gate: [`scripts/validate_domain_source_review_packet.py`](../scripts/validate_domain_source_review_packet.py)
- Domain grounding-manifest proposal builder: [`scripts/build_domain_grounding_manifest_proposal.py`](../scripts/build_domain_grounding_manifest_proposal.py)
- Domain curation bundle builder: [`scripts/build_domain_curation_bundle.py`](../scripts/build_domain_curation_bundle.py)
- Domain curation bundle validator: [`scripts/validate_domain_curation_bundle.py`](../scripts/validate_domain_curation_bundle.py)
- Regulatory miss pattern plan builder: [`scripts/build_regulatory_miss_pattern_plan.py`](../scripts/build_regulatory_miss_pattern_plan.py)
- Regulatory domain intake builder: [`scripts/build_regulatory_domain_intake_packet.py`](../scripts/build_regulatory_domain_intake_packet.py)
- Regulatory domain intake validation gate: [`scripts/validate_regulatory_domain_intake_packet.py`](../scripts/validate_regulatory_domain_intake_packet.py)
- Regulatory domain seed proposal builder: [`scripts/build_regulatory_domain_seed_proposal.py`](../scripts/build_regulatory_domain_seed_proposal.py)
- Regulatory curation bundle builder: [`scripts/build_regulatory_curation_bundle.py`](../scripts/build_regulatory_curation_bundle.py)
- AI pickup bridge: [`docs/CLAUDE_CODE_HANDOFF.md`](CLAUDE_CODE_HANDOFF.md) is the current closeout pickup; root [`PROJECT_BIBLE.md`](../PROJECT_BIBLE.md) maps Claude Code, Codex, and Fable 5-style agents to it and the deeper [`docs/codex/PROJECT_BIBLE.md`](codex/PROJECT_BIBLE.md); root [`Plans.md`](../Plans.md) is a compatibility bridge for older Claude Code handoffs.
- Root file policy: [`ROOT_FILES.md`](../ROOT_FILES.md)
- File purpose policy: [`docs/FILE_PURPOSE_GUIDE.md`](FILE_PURPOSE_GUIDE.md)
- Kaggle Community Benchmark notes: [`docs/KAGGLE_COMMUNITY_BENCHMARK.md`](KAGGLE_COMMUNITY_BENCHMARK.md)
- Copy-ready networked knowledge-sharing Kaggle post: [`docs/kaggle_post_networked_knowledge_sharing.md`](kaggle_post_networked_knowledge_sharing.md)
- Screenshot audit checklist: [`docs/SCREENSHOT_AUDIT.md`](SCREENSHOT_AUDIT.md)

## Archival Rule

If a doc primarily describes the retired appendix ladder, old publish status,
old score projections, or A-01 through A-24 as the active submission path, it
belongs under `docs/_archive/2026-05-16-legacy-notebook-era/` unless it has been
rewritten around the current active Kaggle scope.

Root `kaggle/` must not contain appendix `A-*` folders other than the active
`A-00-omni-experiment-workbench`, and the only root `04-*` folder should be
`04-kaggle-community-benchmark`.
