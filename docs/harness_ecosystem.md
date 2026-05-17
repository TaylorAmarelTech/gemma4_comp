# DueCare Harness Ecosystem

DueCare should not be described as one monolithic harness. The codebase has a
core content-safety harness, but it also has multiple repeatable workflows that
wrap Gemma 4 with preprocessing, post-processing, tools, retrieval, evaluation,
training, graphing, privacy checks, and export contracts.

For project language, use this definition:

> A DueCare harness is any named, repeatable set of steps around Gemma 4 or a
> trust boundary that transforms inputs, adds context, calls tools, evaluates
> outputs, protects privacy, generates training data, or emits auditable
> artifacts for a specific goal.

## Canonical implementation sources

| Source | Role |
|---|---|
| `packages/duecare-llm-chat/src/duecare/chat/harness/__init__.py` | Legacy singular module that still holds the canonical GREP rules, RAG corpus, tool dispatch, and combined grading primitives used by Kernel 01 and A-00. |
| `packages/duecare-llm-chat/src/duecare/chat/harnesses/` | Registered reviewer-facing harness surfaces with `name`, `applied_layers`, `consumes`, `emits`, `spec`, and `register_routes(app)`. |
| `packages/duecare-llm-chat/src/duecare/chat/harnesses/model_interface.py` | Provider-neutral model request/response helper for harnesses that need local Gemma, DueCare adapters, Ollama, OpenAI-compatible endpoints, Anthropic, Gemini, HF endpoints, frontier APIs, or test callables. |
| `packages/duecare-llm-chat/src/duecare/chat/gemma4_runtime.py` | Shared Gemma 4 runtime primitive for loading, unloading, and generating with Unsloth `FastModel`. |
| `packages/duecare-llm-chat/src/duecare/chat/experiment_contracts.py` | Shared experiment profiles for harness comparison, synthetic data, training, and comparison matrices. |
| `kaggle/01-duecare-exploration-workbench/kernel.py` | Canonical live exploration and harness comparison workbench. |
| `kaggle/A-00-omni-experiment-workbench/kernel.py` | Quantitative control plane for benchmark runs, synthetic data, LoRA training, judging, reports, and research graphs. |

The normalized field contract for logic paths, knowledge packs, logic packs,
model I/O, model targets, input/output verification, and privacy boundaries lives in
[`docs/harness_standard_contract.md`](harness_standard_contract.md).

## Universal model-target layer

Every registered harness now declares `model_targets` in its `HarnessSpec`.
This separates the harness workflow from the model provider:

- local Kaggle proof runs use `gemma4_runtime` and the shared Unsloth
  `FastModel` loader;
- local/private deployments can route through `ollama`, `llama_cpp`,
  `transformers`, `unsloth`, or a generic `duecare_model_adapter`;
- cloud or frontier judging can route through `openai_compatible`,
  `anthropic`, `google_gemini`, `hf_inference_endpoint`, or `frontier_api`;
- deterministic gates such as anonymization, search safety, search, and
  import explicitly declare `none` targets so they remain usable without an
  LLM.

The privacy boundary travels with the target. External targets should receive
only redacted, generalized, or policy-approved content.

## Registered harness surfaces

These are the modules exposed through `duecare.chat.harnesses`.

| Harness | Purpose | Gemma 4 role | Status |
|---|---|---|---|
| `chat` | Free-form content prompt processing with persona, GREP, RAG, tools, optional online, imports, traces, and grading hooks. | Required for real answers. | Implemented. |
| `process` | Bulk file review, case-bundle parsing, graph extraction, and graph-chat over local evidence. | Hybrid: deterministic parsing first, Gemma for graph-chat and deeper extraction. | Implemented. |
| `extraction` | Draft typed KnowledgeObject envelopes from source text, documents, or process outputs. | Optional drafter; deterministic hints remain available without a model. | Implemented. |
| `anonymization` | PII and confidential-data gate before sharing or submission. | Optional second review over already-redacted text. | Implemented. |
| `search_safety` | Convert raw search intent into redacted or generalized search phrases before third-party search. | Optional rephrase over already-redacted query. | Implemented as a gate. |
| `search` | Run a selected search backend after query sanitization and return result cards. | Downstream only; search itself is not a model call. | Implemented utility. |
| `import_corpus` | Store local uploaded evidence and snippets for later use by chat, process, and extraction. | No model call; supplies context to other harnesses. | Implemented utility. |

## Broader harness families

The following are also harnesses under the broader DueCare definition because
they encapsulate repeatable logic around Gemma 4, a trust boundary, or an
auditable proof artifact.

| Harness family | Current code path | What it does | Status |
|---|---|---|---|
| Core layer composer | `harness/__init__.py`, `harnesses/_layers.py` | Composes persona, GREP, RAG, tools, online, and imports into the grounding Gemma receives. | Implemented. |
| Content safety response harness | `harnesses/chat`, Kernel 01 compare, A-00 `chat_no_online` | Runs prompts with and without the safety stack, captures traces, and produces comparable outputs. | Implemented. |
| Offline default proof harness | A-00 preconfigured pipeline | Uses `chat_no_online`: persona + GREP + RAG/context + deterministic tools, with internet/import disabled for the default reproducible run. | Implemented. |
| Search anonymization harness | `harnesses/search_safety` | Redacts private facts and can ask Gemma to generalize the query before it reaches a search provider. | Implemented. |
| Online grounding harness | `harnesses/search`, chat online layer, A-00 documented path | Intended path: prompt -> Gemma-anonymized query -> search -> page markdown -> Gemma verification -> KnowledgeObjects -> prompt injection. | Partially implemented; default A-00 run keeps it off. |
| Post-search verification harness | Search result to extraction/chat flow | Should review downloaded pages for relevance, source quality, contradictions, and deanonymization risk before any result is injected. | Planned hardening. |
| Anonymization/deanonymization review harness | `harnesses/anonymization`, A-00 `_redact` | Redacts PII, records hashes, and can run local residual-PII review before hub submission or external calls. | Implemented; external-boundary policy should stay strict. |
| Knowledge ingestion harness | `harnesses/import_corpus`, `harnesses/extraction`, `harness/_governance.py` | Turns local files, snippets, or source bundles into reviewable, versioned knowledge objects. | Implemented. |
| Civil-society fact intake harness | Contribute flow plus import/extraction/anonymization modules | Should process NGO/civil-society emails or submissions into sanitized fact proposals and knowledge objects. | Partially implemented through generic import/extraction; dedicated email intake remains a specialization to build. |
| Research graph harness | `harnesses/process`, A-00 `_extract_research_graph` | Extracts entities, edges, timeline signals, amounts, risks, and graph artifacts from local bundles. | Implemented. |
| Synthetic data generator harness | A-00 `_generate_synthetic`, `SYNTHETIC_GENERATION_PROFILES` | Generates SFT rows, DPO pairs, test prompts, and candidate knowledge facts from harnessed/adversarial prompts. | Implemented. |
| Rubric-polish harness | A-00 `_polish_training_response` | Rewrites training rows toward the DueCare response contract: cited, bounded, privacy-safe, and structured. | Implemented. |
| Fine-tuning harness | A-00 `_training_script`, `TrainRequest`, `TRAINING_PROFILES`, `duecare-llm-training` | Builds LoRA training jobs, checkpoint/resume paths, adapter outputs, and training logs. | Implemented. |
| Evaluation/judge harness | `grade_response_universal`, `grade_response_combined`, A-00 judge selection | Combines deterministic rules with local Gemma or external judge options for final scoring. | Implemented. |
| Report/export harness | A-00 report and activity artifacts | Saves JSON, Markdown, HTML, run outputs, traces, activity events, and comparison summaries for writeups. | Implemented and still being improved. |
| Model runtime primitive | `gemma4_runtime.py` | Standardizes Unsloth `FastModel` load/unload/generate behavior across notebooks. | Implemented primitive; not a user-facing safety harness. |

## Search and online grounding policy

Online grounding can be valuable, but it must not bypass the privacy and
verification harnesses.

The safe target flow is:

1. Identify what public fact is missing.
2. Redact or generalize the search intent locally.
3. Let Gemma produce a sanitized query from the redacted intent.
4. Search only with that sanitized query.
5. Convert pages to bounded snippets or markdown.
6. Run a post-search verification pass for relevance, source quality, conflict,
   and deanonymization risk.
7. Convert accepted facts into KnowledgeObjects.
8. Inject only accepted knowledge objects or cited snippets into the final
   prompt.

For the A-00 preconfigured proof run, online grounding remains off by default
because the demo needs reproducibility and a clean privacy boundary.

## Naming guidance

Use "harness ecosystem" for the full DueCare system. Use "core content-safety
harness" or "chat harness" when referring specifically to persona + GREP + RAG
+ tools + optional online around a prompt.

Avoid saying DueCare is "one harness" unless the sentence is explicitly about
one runtime surface. Better wording:

- "DueCare is a Gemma 4 harness ecosystem for migrant-worker safety."
- "The chat harness is one harness in the ecosystem."
- "A-00 runs the benchmark, synthetic-data, fine-tuning, judging, and report
  harnesses in sequence."
- "The online harness is privacy-gated and should verify search results before
  they become context."

## Current gaps to avoid overstating

- A dedicated civil-society email intake harness is not a separate first-class
  module yet. The current path is generic import -> anonymization -> extraction
  -> reviewer promotion.
- Post-search verification exists as a required architecture direction, but it
  should be hardened before online grounding is used as a default benchmark
  layer.
- External frontier judges can be configured, but the competition default must
  remain runnable without paid API keys.
