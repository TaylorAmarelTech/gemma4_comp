# Kaggle Writeup Draft: DueCare

**Title:** DueCare: Gemma 4 safety infrastructure for migrant-worker protection

**Subtitle:** A local-first Gemma 4 workbench that helps workers, NGOs, platforms, regulators, and researchers detect exploitation, ground answers in public law, preserve privacy, and prove safety lift with reproducible evaluation bundles.

**Track:** Safety & Trust. Special Technology alignment: Unsloth fine-tuning, local Gemma 4 deployment, GGUF and LiteRT export path.

## Summary

DueCare addresses a real and high-stakes gap: migrant workers and the people who support them often need help interpreting recruiter messages, contracts, receipts, screenshots, and case bundles that may contain exploitation indicators. The dangerous parts are frequently hidden in ordinary language: "processing loans," salary deductions, passport safekeeping, contract substitution, forged documents, or corridor-specific fee caps.

A generic chatbot can miss those signals, give generic legal disclaimers, or send sensitive case facts to a cloud service. DueCare instead wraps Gemma 4 in a private, inspectable safety harness. The system runs in a Kaggle session or local environment, keeps raw evidence inside the user-controlled runtime, and exposes every safety step so reviewers can see what changed and why.

## What We Built

DueCare has three core submission surfaces.

Notebook 01 is the exploration workbench. It includes Chat, Harness Comparison, Bulk File Review, Knowledge Extraction, Search Safety, Anonymization, Sync, Status, and Harnesses pages. A shared top model selector loads the active Gemma 4 model once for every page. The comparison page sends the same prompt through two harness configurations and grades both outputs.

Notebook 02 is the focused live demo. It keeps the story narrow: one loaded Gemma 4 model, one polished route through the safety layers, and a clear before-and-after comparison.

Notebook 03 is the video pitch surface. It provides deterministic scenes for recording a three-minute story without waiting on live inference.

Appendix A-00 is the technical proof workbench. It is the control plane for
bulk prompt runs, export/import reruns, rule and LLM judging, knowledge-pack
sync, synthetic-data generation, and LoRA training jobs. The narrower
appendix notebooks remain useful as simple single-claim reproductions.

The workbench has seven harness contracts:

1. Chat: free-form Gemma 4 chat with persona, GREP, RAG, tools, online search, imports, optional image input, and grading.
2. Bulk File Review: ZIP, CSV, or JSONL upload with entity extraction, GREP scanning, person/document linking, local graph construction, and Gemma 4 case briefing.
3. Knowledge Extraction: Gemma 4 drafts standardized knowledge-object envelopes from raw text.
4. Anonymization: regex and NER redaction before evidence crosses a trust boundary.
5. Search Safety: strips PII from outbound search queries before any third-party backend.
6. Search: secondary web-search utility called only after safety sanitization when enabled.
7. Import Corpus: local evidence CRUD. It is intentionally not labeled a Gemma harness because it performs no model call.

## How Gemma 4 Is Used

Gemma 4 is the reasoning engine behind the product, not a decorative dependency.

In Chat, Gemma 4 receives a composed prompt that may include persona guidance, deterministic GREP findings, retrieved public-law context, imported evidence snippets, tool outputs, and optional search results. The UI shows the model-visible path before generation.

In Bulk File Review, Gemma 4 summarizes a locally extracted intelligence graph. The deterministic layer first detects entities, document types, locations, payment patterns, rule hits, and evidence edges. Gemma 4 then produces a case brief using only those facts.

In Knowledge Extraction, Gemma 4 turns messy text into typed knowledge envelopes such as GREP rules, RAG docs, citation edges, context snippets, and rubric dimensions.

In evaluation, Gemma 4 can act as a judge across rubric dimensions. The deterministic grader and LLM grader are separated so users can compare fast rule evidence against semantic judgment.

For post-training, appendix notebooks generate synthetic and composite training data, fine-tune adapters with Unsloth, and export comparison artifacts. The design respects Kaggle's practical one-model-per-session constraint: each run exports a canonical bundle, then later sessions import that bundle to compare base, harnessed, fine-tuned, and fine-tuned plus harnessed conditions.

## Technical Architecture

DueCare is a FastAPI app packaged as `duecare-llm-chat`, with shared static UI, harness modules, and tests. Each harness declares what layers it applies, what data it consumes, what it emits, and which routes it registers. The harnesses share a knowledge-object system: all reusable rules, documents, prompts, schemas, rubric dimensions, tool definitions, and evidence objects use a versioned envelope.

The core safety layers are:

* Persona: anti-trafficking expert instruction.
* GREP: deterministic pattern detection for fee camouflage, debt bondage, passport control, ILO indicators, corridor fee caps, document fraud, employer abuse, and related patterns.
* RAG: public legal and NGO reference retrieval.
* Tools: typed lookups for corridor fees, ILO indicators, NGO contacts, and conventions.
* Online: optional search with PII safety gates.
* Imports: local evidence context.

Every meaningful run can produce a v1.0 appendix bundle with `results.json`, `run.jsonl`, `metadata.json`, and `manifest.json`. Those bundles are the glue between notebooks and make quantitative claims reproducible.

## Evaluation Plan

The submission proves lift in three ways.

First, the live Harness Comparison page shows one prompt with and without the harness, then grades both responses.

Second, A-00 and the appendix evaluation notebooks can run 100+ prompts under one condition, export the responses and metadata, then import that bundle in a later session to run another condition. This supports no-harness, harnessed, fine-tuned, and fine-tuned plus harnessed comparisons without loading multiple models at once.

Third, rule-based and LLM-based grading score each response across prompt-appropriate dimensions. The rubric uses dynamic applicability so N/A is driven primarily by the prompt and task, not by whether a response happened to mention a topic.

## Impact

DueCare is not a replacement for lawyers, caseworkers, or hotlines. It is infrastructure for exercising due care. A worker can ask a private question about recruiter fees or passport retention. An NGO can review a case bundle without uploading raw evidence to a public server. A platform can screen recruitment content before workers see it. A regulator or researcher can compare model behavior with reproducible artifacts.

The positive-change claim is practical: make local Gemma 4 reasoning useful in places where privacy, trust, and limited connectivity matter.

## Current Submission Assets

* Public repository: `https://github.com/TaylorAmarelTech/gemma4_comp`
* Live demo: attach the active Cloudflare tunnel URL from Notebook 02.
* Video: attach the public YouTube link from the Notebook 03 recording.
* Media gallery: cover image plus screenshots of Chat, Harness Comparison, Bulk File Review, and the appendix report.

## Why This Fits Gemma 4 Good

DueCare targets Safety & Trust with real technical depth: local Gemma 4 inference, native function-style tools, multimodal evidence intake, retrieval-grounded answers, rule and LLM evaluation, synthetic data generation, Unsloth adapter training, and exportable proof bundles. The product story is simple: vulnerable workers need safer help, sensitive evidence must stay private, and every safety claim should be inspectable.
