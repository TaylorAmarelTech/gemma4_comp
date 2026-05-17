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
