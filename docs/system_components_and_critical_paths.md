# DueCare System Components And Critical Paths

This document is the stable map for the active DueCare/Gemma 4
submission. It intentionally avoids exact inventory counts except for
coarse public claims such as "100+ GREP rules" or "50+ RAG documents."
Exact catalog sizes belong in runtime APIs, generated reports, and
exported artifacts.

## Current Active Scope

The active Kaggle surface is two kernels:

| Kernel | Purpose |
|---|---|
| `kaggle/01-duecare-exploration-workbench/` | Interactive exploration, harness comparison, search safety, extraction, anonymization, grading, and layer inspection. |
| `kaggle/02-live-demo/` | Focused reviewer demo using the shared Gemma runtime and the same harness primitives. |

Archived appendix notebooks, the A-00 experiment console, and task-notebook
snapshots are historical context. They are not the current competition path
unless they are explicitly revived by a new decision. Root `kaggle/` should
not contain appendix `A-*` folders, and the only root `04-*` folder should be
`04-kaggle-community-benchmark`.

## Main Components

| Component | Purpose | Main Code |
|---|---|---|
| Gemma runtime | Standard local inference loader, generation defaults, chat template, and model lifecycle. | `packages/duecare-llm-chat/src/duecare/chat/gemma4_runtime.py` |
| Harness registry | Declares registered harness modules, their routes, capabilities, model targets, and trust boundaries. | `packages/duecare-llm-chat/src/duecare/chat/harnesses/` |
| Core chat harness primitives | Canonical GREP rules, RAG corpus, tool dispatch, contacts, grading helpers, and shared comparison behavior. | `packages/duecare-llm-chat/src/duecare/chat/harness/__init__.py` |
| Knowledge objects and packs | Portable facts, rules, docs, rubrics, contacts, tool metadata, and extracted evidence envelopes. | Harness JSON packs, import/export routes, and A-00 generated artifacts |
| Universal model interface | Normalizes local model calls and external endpoints such as Ollama, Anthropic, OpenAI-compatible services, Gemini, or future hosted judges. | `packages/duecare-llm-chat/src/duecare/chat/harnesses/model_interface.py` |
| Archived A-00 experiment pipeline | Orchestrates benchmark arms, synthetic row generation, optional training, checkpoint handling, judging, and report generation. | `kaggle/_archive/notebooks/A-00-omni-experiment-workbench/kernel.py` |
| Evaluation and judging | Combines deterministic rubric scoring with optional LLM judging and produces comparison summaries. | `duecare.chat.harness`, A-00 judging helpers |
| Report and artifact export | Saves JSON, markdown, HTML, activity logs, training outputs, adapters, and checkpoint references. | A-00 export/report helpers |

## Harness Definition

In this project, a harness is any repeatable package of preprocessing,
context loading, model calls, tools, postprocessing, verification,
grading, or artifact emission around a model.

Registered harnesses expose a stable contract:

- `name`
- `applied_layers`
- `register_routes(app)`
- optional `HarnessSpec`
- optional `compose`
- optional `load_knowledge`
- optional `emit_training_row`

The broader harness ecosystem also includes pipeline harnesses that
are not always separate route modules: synthetic data generation,
rubric polishing, fine-tuning/checkpointing, online grounding,
post-search verification, evaluation/judging, and report export.

## Registered Harnesses

| Harness | Primary Role |
|---|---|
| `chat` | Persona, GREP, RAG, tools, imports, optional online context, and response policy. |
| `process` | Bulk review, evidence processing, graph extraction, and graph chat. |
| `extraction` | Converts source text into typed knowledge-object candidates. |
| `anonymization` | Redacts or flags PII and sensitive material before sharing. |
| `search_safety` | Converts prompts into safer, anonymized search intent before external search. |
| `post_search_verification` | Reviews external search results before they can enter chat, extraction, or knowledge ingestion. |
| `search` | Executes search after safety checks and marks results as unverified candidates. |
| `import_corpus` | Imports local evidence/context into the in-kernel retrieval pool. |

If the registry changes, this table should change once. Public copy
should otherwise say "registered harnesses" or "harness ecosystem" so
ordinary catalog growth does not create drift.

## Knowledge And Logic Objects

Knowledge objects are typed, portable units that harnesses can consume
or emit. Common families:

| Family | Examples | Consumer |
|---|---|---|
| Matching knowledge | GREP rules, classifiers, severity labels | Chat, process, evaluation |
| Grounding knowledge | RAG docs, citations, corridor profiles | Chat, search verification, reports |
| Tool knowledge | Tool schemas, examples, lookup tables | Chat tools, A-00 harnessed runs |
| Evaluation knowledge | Rubrics, judge questions, grade weights | Grade endpoints, A-00 final judging |
| Extracted evidence | Facts, entities, edges, timelines, risks | Process, extraction, report export |
| Graph-extraction logic | Edge quality dimensions, pointed edge questions, typed edge schemas | Process, graph-chat, knowledge promotion |
| Training knowledge | Synthetic SFT rows, polished examples, rejected rows | A-00 training and checkpoint flow |

The envelope is intentionally broad enough for full-document and
long-document use cases. A publication, case, statute, Palermo Protocol
text, IOM/UN report, or multi-page PDF should enter as a source
document object with provenance, hashes, page/chunk metadata, extracted
text, and derived citations/facts. Harnesses should consume the vetted
chunks and derived facts, not assume that a default synthetic run has
parsed every raw publication.

In the current A-00 guided proof path, synthetic training rows use
prompt seeds, shared GREP/RAG/tools, and loaded knowledge packs. Raw
IOM, UN, court, jurisdictional, or PDF corpora affect those rows only
after they have been imported, chunked, synced, or otherwise promoted
into vetted knowledge packs/source-document objects.

The north-star direction is to keep moving logic out of hardcoded
duplicates and into versioned packs, `HarnessSpec`, and reusable
knowledge-object contracts.

For bulk document review, the process harness now treats edge
generation as its own evaluation surface. It uses pointed graph
questions and edge-quality dimensions for source grounding, typed
relations, entity roles, payments, document control, coercion,
journey-stage sequencing, cross-document links, contradictions,
uncertainty, and PII-minimized knowledge candidates. A fine-tuned
Gemma 4 adapter trained on reviewed document-classification and
graph-edge examples can be loaded for better page routing, edge typing,
and bulk file edge generation while preserving the same local-only
review gate.

## Critical Paths

### Kernel 01 Exploration

1. User submits a prompt, document, or comparison request.
2. The app loads the selected harness layers.
3. GREP, RAG, tools, imports, and optional online context produce a
   traceable merged prompt.
4. Gemma is called through the shared runtime or configured backend.
5. The response is graded, traced, and shown with layer-level evidence.
6. Optional extraction/import flows emit knowledge-object candidates.

### Kernel 02 Live Demo

1. The focused demo starts the shared runtime and app surface.
2. The user runs the same core harness behavior without the broad
   experiment controls.
3. The output demonstrates the safety and grounding loop quickly.

### Archived A-00 Quantitative Proof

1. The user selects a model and run size.
2. A-00 checks loaded model state, memory, and disk conditions.
3. Base Gemma loads through `Gemma4Runtime`.
4. The selected prompts run without the harness.
5. The same prompts run with the offline DueCare harness.
6. Harnessed output can generate synthetic training rows.
7. Optional LoRA fine-tuning runs with checkpoint/save controls.
8. The fine-tuned adapter is loaded and evaluated with and without the
   harness.
9. The judge model or endpoint evaluates outputs using combined
   deterministic + LLM judging.
10. Reports, activity logs, raw run outputs, adapters, and checkpoint
    metadata are saved under Kaggle working paths.

Key A-00 runtime knobs:

- `DUECARE_A00_BENCHMARK_MAX_NEW_TOKENS` controls the response
  budget for benchmark arms. It defaults to `1200`, which gives
  presentation-quality answers more room than the old short smoke
  budget while staying well below the full context window.
- `DUECARE_A00_INFERENCE_MAX_SEQ_LENGTH` controls the shared Gemma
  inference context window used by benchmark generation and final
  grading. It defaults to a long-context setting so full prompts,
  responses, harness traces, and grading instructions fit.
- `DUECARE_A00_COMBINED_JUDGE_MAX_NEW_TOKENS` controls the structured
  output budget for the combined rule + LLM judge. It defaults to
  `2048` so judge JSON has headroom without treating output budget as
  another full context window.
- `A00_TRAINING_TIMEOUT_SEC`, `training_save_steps`, and
  `training_resume_from_checkpoint` control long LoRA training runs,
  checkpoint cadence, and resume behavior.
- A-00 run summaries and CSV exports include `response_hygiene`
  diagnostics for visible reasoning scaffolds, near-budget answers,
  and likely truncation. These flags are audit metadata only; the
  measured response text is preserved unchanged.

### Online Search Safety

1. A prompt or analyst request is reduced to an anonymized search
   intent by the search-safety harness.
2. External search runs only after that safety gate.
3. Search results are treated as unverified candidates.
4. The post-search verification harness checks source quality,
   relevance, contradiction markers, and deanonymization risk.
5. Only verified or explicitly reviewable summaries can feed chat,
   extraction, or knowledge-object promotion.

### Training Flywheel

1. Harnessed runs produce structured traces and candidate SFT rows.
2. Synthetic/rubric-polish logic filters weak rows.
3. A-00 trains with checkpointing and adapter saves.
4. Evaluation compares stock, stock+harness, fine-tuned, and
   fine-tuned+harness arms.
5. Good outputs, failures, and new evidence can feed future knowledge
   packs after review.

## Users And Use Cases

| User | Primary Need | Main Surface |
|---|---|---|
| Migrant worker | Private, plain-language warning signs and next steps. | Android app, future channels, worker-facing guidance. |
| Caseworker / NGO | Intake triage, grounded summaries, referrals, report drafts. | Kernel 01, local/office deployment, contact packs. |
| Regulator / consulate | Pattern analysis, corridor risk, official response drafting. | Harnessed chat, process/extraction, reports. |
| Platform safety team | Moderation risk trace and policy auditability. | API, classifier, dashboard integrations. |
| Researcher / judge | Reproducible comparisons and quantitative proof. | A-00, reports, harness-lift docs. |
| Developer / integration partner | Embeddable APIs, model targets, pack contracts. | FastAPI routes, harness registry, model interface. |

## Drift Rules

1. Static docs should avoid exact live catalog counts.
2. Runtime APIs and generated reports may show exact current counts.
3. Kernel 01 and Kernel 02 should share model loading through
   `Gemma4Runtime` for inference.
4. Archived A-00 should consume shared GREP/RAG/tool/grading primitives rather
   than duplicating them.
5. External model and judge endpoints should flow through the universal
   model interface where practical.
6. Search results should not enter downstream context without the
   search-safety and post-search verification gates.
7. Archived docs and kernels should stay archived unless a new current
   scope decision brings them back.
