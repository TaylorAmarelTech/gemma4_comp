# DueCare: A Gemma 4 Harness Ecosystem for Migrant-Worker Safety

**Track:** Safety & Trust. Technical alignment: local Gemma 4 inference,
Unsloth LoRA fine-tuning, combined rule + LLM judging, and exportable evidence
bundles.

## Summary

DueCare wraps Gemma 4 with a harness ecosystem for migrant-worker exploitation
risk: deterministic GREP rules, RAG/context, tool lookups, search-safety and
anonymization gates, synthetic-data generation, fine-tuning, judging, and
reports. The goal is practical: help workers, NGOs, regulators, and researchers
inspect recruiter-fee, passport-retention, debt-bondage, and coercion signals
without forcing sensitive evidence into an opaque remote workflow.

## Active Proof Path

The current submission uses three active Kaggle kernels:

1. `kaggle/01-duecare-exploration-workbench/` - broad interactive workbench.
2. `kaggle/02-live-demo/` - focused demo and video path.
3. `kaggle/A-00-omni-experiment-workbench/` - quantitative control plane.

A-00 is the main measurable proof. It runs baseline Gemma, harnessed Gemma,
synthetic SFT generation, optional LoRA fine-tuning, fine-tuned arms, final
combined rule + LLM judging, and report export while keeping one model resident
at a time.

## Harness Design

The default offline proof harness uses:

- Persona guidance.
- GREP rule hits.
- RAG/context retrieval.
- Deterministic tools.
- Internet and import disabled unless explicitly enabled.

This default should match the Kernel 01 comparison path. Online grounding is a
separate optional harness family and should be gated by search anonymization and
post-search verification before it is used for sensitive prompts.

## Live Bulk File Review Walkthrough

The exploration workbench includes a Bulk File Review surface
(`/static/process.html`) that lets a reviewer upload a case bundle, watch
local deterministic processing, inspect the extracted intelligence graph,
and ask graph-chat questions over it — all without a loaded model on the
happy path.

The shipped `case_files_streamlined_demo.zip` (synthetic PH-HK domestic
worker bundle, ~75 KB, five documents) drives the canonical demo. The full
step-by-step script is `docs/bulk_file_review_demo_script.md`. Key
observable behaviors:

- **Processing produces 42 typed edges** across `dated_evidence`,
  `journey_stage_observation`, `fee_amount_observed`, `filed_under`,
  `located_at`, and `salary_deduction_signal`. The intelligence graph
  renders on the page; row IDs and source paths stay inside their cards.
- **Completion is honest.** When media items remain queued for OCR or
  Gemma vision review, the final 100% completion event says exactly that
  ("Deterministic parsing complete; N media asset(s) remain queued...").
  Text-only bundles say "no media items queued". The page never claims
  multimodal work finished when it was only queued.
- **The flagship TIP question gets a deterministic answer with cited
  rows.** Asking "Which rows support fee camouflage and restricted
  provider choice?" trips a dedicated branch that returns
  `analysis_kind="fee_camouflage_and_provider_choice"`, surfaces the
  available `fee_amount_observed` / `salary_deduction_signal` and
  `located_at` / `filed_under` / `journey_stage_observation` proxy
  edges, cites only row IDs from the bundle, and explicitly points the
  reviewer at the optional local Gemma edge pass as the upgrade path to
  explicit `fee_camouflage_evidence` and `provider_choice_restriction`
  edges. No hallucinated rows.
- **Review gate is reviewer-only.** "Mark review complete" is purely a
  client-side state change; the activity log records "no processing or
  model call was started". No silent model load.
- **Optional Gemma edge pass degrades gracefully.** If no model is
  loaded, `/api/process/graph-extract/start` completes with
  `status=deterministic_no_model` and the existing deterministic edges
  remain visible. No forced model popup.

Each of these behaviors is pinned by contract tests in
`packages/duecare-llm-chat/tests/test_process_bulk_review.py` so a
regression in the demo path trips CI.

## Training And Evaluation

A-00 can generate synthetic rows from harnessed outputs and train a small LoRA
adapter with checkpoint/resume enabled. The final report compares baseline,
baseline+harness, fine-tuned, and fine-tuned+harness arms when training is run.
Scoring uses combined rule + LLM judging.

Larger Gemma or frontier judges may improve final grading quality, but the
default proof run remains local and reproducible.

## Evidence

The important output is the artifact bundle under `/kaggle/working`: activity
logs, prompts, responses, traces, synthetic rows, training metadata,
checkpoints, adapter paths, judging rows, charts, HTML/Markdown/JSON reports,
and a manifest.

## Why It Fits

DueCare targets Safety & Trust with inspectable local reasoning. The model is
not treated as sufficient by itself; it is wrapped with explicit context,
policies, tools, privacy gates, and evaluation. That is the core contribution.
