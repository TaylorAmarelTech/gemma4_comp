# CLAUDE.md - DueCare project context

> Context for Claude / Claude Code sessions working on this project.
> If you are a new AI assistant picking up this project, read this first.

## Current operating brief (2026-05-19)

- Active submission work is the three-kernel path: `kaggle/01-duecare-exploration-workbench`, `kaggle/02-live-demo`, and `kaggle/A-00-omni-experiment-workbench`.
- Optional benchmark work lives in `kaggle/03-universal-llm-benchmark` for arbitrary endpoint comparisons and `kaggle/04-kaggle-community-benchmark` for Kaggle-native Community Benchmark tasks. Neither replaces the three-kernel recording path.
- The public story has six setup lanes in this order: Platform safety, NGO & regulator, Individual worker / mobile, Researcher, Anonymized knowledge sharing, Developer / integration partner.
- The workspace has 17 `duecare-llm*` package directories. The latest verified local collection is 675 package tests collected; do not claim a full pass unless you ran the full suite.
- Documentation edits should follow `docs/DOCUMENTATION_GUIDE.md`; agent edits should also honor the root `AGENTS.md`.
- Repo-organization edits should also keep `docs/FILE_PURPOSE_GUIDE.md` and the relevant directory index current.
- Keep generated report files out of commits unless Taylor explicitly asks to publish them.

## Three overarching goals (every prompt, every action)

1. **Impact & Vision (40 pts)** — from the video. Real-world problem,
   inspiring vision, tangible potential for positive change.
2. **Video Pitch & Storytelling (30 pts)** — exciting, engaging,
   well-produced, tells a powerful story.
3. **Technical Depth & Execution (30 pts)** — verified from the code
   repository and writeup. Innovative use of Gemma 4's unique features
   (native function calling, multimodal understanding). Real, not faked
   for the demo.

**70 of 100 points live in the video.** Every decision is evaluated
against these three. If a proposed action doesn't advance at least one
of them, it gets cut. Full rule: `.claude/rules/00_overarching_goals.md`.

## Auto-loaded rules

`.claude/rules/*.md` files are auto-loaded by Claude Code at the
project memory level. Currently:

- `00_overarching_goals.md` — the three rubric goals
- `10_safety_gate.md` — no PII in git / logs / artifacts
- `20_code_style.md` — Python 3.11+, Pydantic v2, Protocol-based
- `30_test_before_commit.md` — duecare test before PR
- `40_forge_module_contract.md` — folder-per-module pattern
- `50_publish_strategy.md` — GitHub + multi-package PyPI + Kaggle
- `60_notebook_presentation.md` — Kaggle-safe styling, no-truncation, pandas Styler + Markdown over raw HTML; shared helpers in `scripts/_notebook_display.py`
- `70_workbench_ui_primitives.md` — every page needs an activity log + status discoverability + sample artifact + trust boundary; model loading defaults to ONE model at a time (multi is opt-in via settings); shared `.dc-activity-log` CSS + `_activity_log.js` helper

Additional root guidance:

- `AGENTS.md` - cross-agent repo orientation and validation commands.
- `docs/DOCUMENTATION_GUIDE.md` - canonical public facts and documentation claims policy.

## Recording-critical surfaces

Before a video recording pass, treat these three Kaggle kernels as the
blocking set:

- `kaggle/01-duecare-exploration-workbench`: broad reviewer workbench.
  Every page should load from a direct URL, share the top model state,
  show an activity log, and expose the trust boundary for its workflow.
- `kaggle/02-live-demo`: focused interactive demo path. Use cached or
  pre-generated scenes when live model latency would weaken the story.
- `kaggle/A-00-omni-experiment-workbench`: technical proof control plane.
  The home page should only offer two navigation cards: Preconfigured
  Harness, Training, and Evaluation; and Custom. The preconfigured page
  should expose only the selected Gemma model and prompt count before
  running the guided proof. Advanced controls belong on Custom only.

`kaggle/03-duecare-video-pitch` and appendix notebooks other than A-00 are
archived for the current submission push. Do not revive or broaden them unless
Taylor explicitly asks.

Do not hardcode volatile phone numbers, URLs, fee caps, wage rules, or
office names into training targets or page copy unless they are also
represented as versioned knowledge objects. Stable response structure,
privacy boundaries, refusal style, ILO indicator reasoning, and evidence
citation habits are appropriate for fine-tuning. Volatile contacts and
current rules should come from tools, RAG, or synced knowledge packs.

## Canonical Gemma 4 runtime and A-00 proof path (2026-05-16)

The source of truth for local Gemma 4 loading is
`packages/duecare-llm-chat/src/duecare/chat/gemma4_runtime.py` and the trace
doc at `docs/model_loading_trace.md`.

All active Kaggle kernels must use the shared `Gemma4Runtime.load()` primitive
for inference model loading. It follows the known-working Unsloth FastModel
recipe:

```python
from unsloth import FastModel

model, tokenizer = FastModel.from_pretrained(
    model_name=resolved_model_ref,
    dtype=None,
    max_seq_length=max_seq_length,
    load_in_4bit=True,
    full_finetuning=False,
    device_map=device_map,  # "balanced" for 31B / 26B-A4B on 2x T4; "auto" otherwise
)
```

After loading, the runtime applies `get_chat_template(...,
chat_template="gemma-4-thinking")`; generation defaults to
`temperature=1.0`, `top_p=0.95`, and `top_k=64`.

Path trace:

- Kernel 01: `/api/load-model` -> `load_gemma()` -> `Gemma4Runtime.load()`.
- Kernel 02: `/api/live/model/load` and startup -> `load_gemma_shared()` ->
  `_LIVE_MODEL_RUNTIME.load()`.
- A-00: `/api/a00/pipeline/run` -> `_create_pipeline_job()` ->
  `_run_pipeline_job()` -> `_prepare_base_model_for_pipeline()` /
  `_load_model_runtime()` -> `A00_MODEL_RUNTIME.load()`.

A-00 fine-tuning is the exception because adapter training uses the Unsloth
training path, not the inference path: `FastModel.from_pretrained()` ->
`FastModel.get_peft_model()` -> `SFTTrainer/SFTConfig` ->
`train_on_responses_only()`.

A-00 preconfigured pipeline contract:

- No dry-run default. The selected Gemma model loads automatically when the
  user starts the preconfigured pipeline.
- No top-banner model/custom buttons. The banner can show status and shutdown
  only if needed; model choice lives in the page body.
- Default model path is the small Gemma path for Kaggle T4 proof runs
  (`google/gemma-4-2b-it` resolving to `unsloth/gemma-4-E2B-it` unless a
  Kaggle-attached model exists).
- Default prompt set is `chat_safety_core`, default prompt count is 2 for the
  fastest real smoke proof.
- Baseline arm uses `baseline_harness_profile="none"`.
- Harnessed arms use `harness_profile="chat_no_online"`: Persona + GREP +
  RAG/context + deterministic tools. Internet and Import are off for the
  default proof path.
- Final scoring uses the same grading primitives as Kernel 01:
  `duecare.chat.harness.grade_response_combined` and
  `grade_response_universal`, with combined rule + LLM judging at the end.
- The activity log should show clear user-facing steps: check loaded model,
  unload/clear memory if needed, check/clean disk, download/load selected
  model with shared FastModel runtime, preflight generation, run baseline,
  run harnessed, generate synthetic rows, fine-tune, save adapter, load
  adapter, run fine-tuned baseline/harnessed arms, reload normal Gemma for
  grading, run combined grading, generate report, save report.

Kernel 01 comparison page remains the behavior reference for harness parity:
`create_app(**default_harness())` wires Persona, GREP, RAG, Tools, and Online
surfaces; A-00's preconfigured proof intentionally uses the offline subset
`chat_no_online` so the run is reproducible and does not require web/search
credentials.

## Universal harness/model abstraction (2026-05-16)

Do not describe DueCare as one hardcoded Gemma harness. The registered
harnesses expose a provider-neutral contract through `HarnessSpec`:

- `logic_paths`: named workflow paths and verification checks.
- `knowledge_packs`: facts/context a harness consumes.
- `logic_packs`: prompts, schemas, tools, rubrics, and backend registries.
- `model_io`: what reaches a model and what comes back.
- `model_targets`: local Gemma, DueCare adapter, Ollama,
  OpenAI-compatible, Anthropic, Gemini, HF endpoint, frontier API, callable,
  or no-model targets.
- `input_verification`, `output_verification`, and `privacy_boundaries`.

The implementation source is
`packages/duecare-llm-chat/src/duecare/chat/harnesses/base.py`.
The portable model caller is
`packages/duecare-llm-chat/src/duecare/chat/harnesses/model_interface.py`.

For Kaggle proof runs, local Gemma 4 still uses `Gemma4Runtime.load()`.
For broader deployments, harnesses should call a configured model through
the universal request/response shape or a `duecare-llm-models` adapter rather
than hardcoding a provider-specific SDK in a route handler. External frontier
targets must receive only redacted, generalized, or policy-approved content.

## Workbench model-loading UI source of truth (2026-05-19)

Kernel 01 uses one universal browser-side model service. Do not add model
selectors, load buttons, logs, or lightboxes directly to individual pages.

Source files:

- `packages/duecare-llm-chat/src/duecare/chat/static/_nav.html`
- `packages/duecare-llm-chat/src/duecare/chat/static/_nav.js`
- `packages/duecare-llm-chat/src/duecare/chat/static/_chrome.css`
- `packages/duecare-llm-chat/src/duecare/chat/static/models.html`

Contract:

- The top status strip shows only concise model state.
- The body-level model layer owns the selector, progress bar, status text,
  load log, refresh, close, and load-selected actions.
- Pages call `window.dcWbModelService.open()`, `.refresh()`,
  `.loadSelected()`, `.loadVariant(id)`, `.ensureReady()`, or `.status()`.
- `_nav.js` removes stale duplicate chrome if older templates inject more than
  one shell or a nested model popover.
- Tests that cover this contract live in
  `packages/duecare-llm-chat/tests/test_compare.py` and
  `packages/duecare-llm-chat/tests/test_harness_workbench.py`.

## Execution phases (the 4-phase arc)

| Phase | Name | Core Question | Deliverable |
|---|---|---|---|
| 1 | **Exploration** | What can Gemma 4 do out of the box? | Baseline report + failure taxonomy |
| 2 | **Comparison** | How does it compare to GPT-OSS, Qwen, Llama, Mistral, DeepSeek? | Cross-model comparison + public benchmark |
| 3 | **Enhancement** | Can we improve via RAG + fine-tuning (Unsloth)? | Fine-tuned weights on HF Hub + ablation |
| 4 | **Implementation** | Can the enhanced model power real-world deployment? | Demo apps + public UI + on-device runtime |

Each phase tests 4 capabilities: guardrails, anonymization, document
classification, key fact extraction. Details: `docs/project_phases.md`.

## Independent components (the full pipeline)

The project is composed of **independent, testable components** that
form a complete pipeline from raw data to deployed model. Each
component can be developed, tested, and used separately.

### A. Data Pipeline (feeds training + evaluation)

```
[A1] Data Loader        → Load existing 21K OSS benchmark prompts/tests
         │
[A2] Data Scraper       → Scrape domain-specific info (ILO reports,
         │                 court cases, policy docs, news articles)
         │
[A3] Document Processor → Extract facts, entities, legal citations,
         │                 fee structures from raw documents
         │
[A4] Prompt Generator   → Create NEW prompts and tests from extracted
         │                 facts (graded response examples, worst→best)
         │
[A5] Data Labeler       → Label and classify: sector, corridor, ILO
         │                 indicators, attack category, severity grade
         │
[A6] Anonymizer         → Hard gate: detect + redact PII before
         │                 anything downstream sees the data
         │
[A7] Dataset Builder    → Assemble labeled, anonymized data into
                           training-ready JSONL splits (Unsloth chat format)
```

**A1 — Data Loader:** Reads from `_reference/trafficking-llm-benchmark-gitlab/`
(21K public tests) and from the author's existing notebooks. Outputs
`RawItem` Pydantic objects with provenance. Also reads any seed prompts
from `configs/<project>/domains/<id>/seed_prompts.jsonl`.

**A2 — Data Scraper:** Playwright + stealth stack for web scraping.
Domain-specific scrapers for ILO databases, court filing repositories
(PACER, AustLII, BAILII), FATF/FATCA publications, NGO reports. Each
scraper outputs `RawDocument` with URL, fetch timestamp, and raw text.
Adapted from `_reference/trafficking_llm_benchmark/src/scraper/`.

**A3 — Document Processor:** NLP pipeline that extracts structured
information from raw documents: named entities, legal citations
(ILO C029, C181, RA 8042), monetary amounts, employer names, fee
structures, migration corridors, dates. Outputs `ExtractedFact` records
with source provenance.

**A4 — Prompt Generator:** Takes `ExtractedFact` records and generates
new evaluation prompts with graded response examples (5-point scale:
harmful → incomplete → adequate → good → best). Uses templates from
domain packs + the existing 21K benchmark patterns. This is where the
dataset GROWS beyond the original benchmark.

**A5 — Data Labeler:** Classifies each prompt/response pair along
multiple axes: sector (domestic work, fishing, construction, agriculture),
migration corridor, ILO forced-labor indicators, attack category
(social engineering, document fraud, fee manipulation, coercion),
severity grade. Can use Gemma 4 itself as a labeler (bootstrapping).

**A6 — Anonymizer:** The existing Anonymizer agent. Hard gate. PII
detection via regex + NER, redaction via tagged replacement, audit
log with `sha256(original)`. Nothing downstream sees raw PII.

**A7 — Dataset Builder:** Takes labeled, anonymized data and produces
training-ready datasets: Unsloth chat-format JSONL, train/val/test
splits, deduplication, balance across domains/categories/grades.
Outputs provenance manifest linking every training example to its
source chain.

### B. Model Pipeline (training + export)

```
[B1] Fine-Tuner         → Unsloth + LoRA on Gemma 4 E4B
[B2] Evaluator          → Run benchmark suite (stock vs. enhanced)
[B3] Exporter           → Merge LoRA → GGUF (llama.cpp) + LiteRT
```

### C. Evaluation Pipeline (the agentic harness)

```
[C1] Model Adapters     → Unified Model protocol across 8 backends
[C2] Domain Packs       → Pluggable safety domains (YAML + JSONL)
[C3] Capability Tests   → 9 standardized tests (guardrails, grounding, etc.)
[C4] Agent Swarm        → 12 autonomous agents orchestrated by a supervisor
[C5] Workflow Runner    → DAG-based multi-step evaluation workflows
[C6] Reporting          → Historian agent → markdown reports with provenance
```

### D. Delivery Pipeline (publishing + demo)

```
[D1] Kaggle Publisher   → Manual copy/paste workflow for kernels + wheels
[D2] HF Hub Publisher   → Upload weights + model cards
[D3] Demo App           → FastAPI web app for live evaluation
[D4] Video Materials    → Script, screenshots, demo recordings
```

## Multi-harness architecture (2026-05-14)

Every reviewer-facing safety surface in the kernel is a harness module: a
self-contained component exposing `name`, `applied_layers: tuple[str, ...]`,
`consumes`, `emits`, and `register_routes(app)`.

Current contract:

- PRIMARY Gemma-backed harnesses: `chat`, `process`, `extraction`
- PRIMARY hard safety gates: `anonymization`, `search_safety`, `post_search_verification`
- SECONDARY utilities: `search`, `import_corpus`

Use the word "harness" carefully. `search` and `import_corpus` are utility
surfaces unless they are feeding a Gemma-backed harness. `anonymization` and
`search_safety` are safety gates because their main job is protecting trust
boundaries before model or third-party calls.

Bulk File Review is now the process harness name. It accepts ZIP, CSV, JSONL,
text, images, and PDFs. Text and extractable PDF pages are chunked locally.
Scanned PDFs and images become explicit OCR plus Gemma 4 vision work items so
the UI never pretends a media file has been read when it has only been queued.

Each handler should call `harnesses._training_log.log_interaction(...)` at
completion when it produces model-relevant input or output. The harness
boundary is also the per-task fine-tuning data boundary: one JSONL stream per
harness at `/kaggle/working/training/<harness>.jsonl`.

Full pattern plus 10-step recipe for new harnesses and multi-rubric review:
@docs/harness_pattern.md

Broader project inventory and wording rules:
@docs/harness_ecosystem.md

Standard fields for generalized logic paths, knowledge packs, logic packs,
model I/O, input/output verification, and privacy boundaries:
@docs/harness_standard_contract.md

### A-00 synthetic data and small-model retraining

A-00 is the control plane for technical proof. It should be able to:

- generate rubric-polished SFT and DPO rows with `generator_mode=rubric_polisher`
- mark stable knowledge for memorization and volatile facts for tool calls
- create a tiny E2B or E4B fine-tune smoke job before a full Kaggle GPU run
- export prompt, response, trace, grade, timing, cost, and provenance bundles

Training data should teach structure, not stale phone numbers. Memorize stable
reasoning habits, refusal behavior, ILO indicator categories, privacy
boundaries, and evidence-first response shape. Use tools or vetted knowledge
packs for hotline numbers, addresses, current advisories, fee caps, wage rules,
and fresh statutes.


### Naming convention (post-Phase 9)

The word **"harness"** is used three ways. Be explicit:

| Term | Refers to | Example |
|---|---|---|
| **harness module** | A subfolder under `harnesses/<name>/` | `chat/`, `process/`, `extraction/` |
| **safety layer** | One callable in `applied_layers` tuple | "the GREP layer fired" |
| **harness ecosystem** | The full DueCare substrate around Gemma 4: runtime, privacy, search, graph, synthetic-data, training, judging, and report harnesses | "DueCare is a Gemma 4 harness ecosystem" |

The legacy singular module `duecare.chat.harness` (no `s`) is the
ORIGINAL implementation — `default_harness()`, `GREP_RULES`, `RAG_CORPUS`,
`_TOOL_DISPATCH`. New work goes in `duecare.chat.harnesses` (with `s`).
Both coexist; see @docs/MIGRATION_HARNESS_PATTERN.md.



## Three deployment modes (see docs/deployment_modes.md)

1. **Enterprise Integration** — waterfall detection at social media /
   job board scale. Quick keyword filter → Gemma 4 analysis → warning
   popup / resource links / moderation queue. Like Facebook's suicide-
   prevention prompts but for trafficking.
2. **Worker-Side Tool** — browser extension, WhatsApp bot, or mobile
   app that runs Gemma 4 entirely on-device via LiteRT. Workers paste
   suspicious messages and get localized legal info + hotline numbers.
   Raw worker chats, IDs, contact details, and private documents stay
   on the worker device unless the worker explicitly creates a sanitized
   submission.
3. **Agency/NGO Dashboard** — FastAPI + web UI for batch evaluation,
   compliance monitoring, model comparison, and regulatory reporting.
   Agencies can fine-tune Gemma 4 on their specific regulations.

## What this project is

A submission for the **Gemma 4 Good Hackathon** on Kaggle (2026-04-02 through
2026-05-18, $200K prize pool across Main/Impact/Special Technology tracks).

**Concept:** Fine-tune Gemma 4 E4B on the author's existing 21K-test
migrant-worker trafficking benchmark (graded response examples, worst->best)
to produce a local, on-device LLM safety judge deployable via llama.cpp /
LiteRT. NGOs and regulators who cannot send sensitive case data to frontier
APIs get a private evaluator they can run on a laptop.

**Tracks targeted:**
- Impact Track -> Safety & Trust ($10K)
- Special Technology Track -> Unsloth ($10K, for the fine-tune itself)
- Special Technology Track -> llama.cpp or LiteRT ($10K, for on-device)
- Main Track if execution is strong ($10K-$50K)

## The author (user) is Taylor Amarel

Taylor Amarel is the author of the existing *LLM Safety Testing Ecosystem*
for migrant-worker protection, which lives in `_reference/`. Specifically:

- `_reference/README.md` - ecosystem overview
- `_reference/CLAUDE.md` - the master framework's AI-assistant guide
- `_reference/ARCHITECTURE_PLAN.md` - the underlying data model and schemas
- `_reference/trafficking_llm_benchmark/` - 300K+ lines of benchmark code
- `_reference/trafficking-llm-benchmark-gitlab/` - 21K-test public release
- `_reference/llm-safety-framework-public/` was **excluded from the copy**
  (5.1 GB); it lives only in the original source folder at
  `C:\Users\amare\OneDrive\Documents\Migrant_Worker_LLM_Test_Benchmark_Trafficking_Bondage_Etc\`

Treat Taylor as a domain expert on trafficking, ILO frameworks, LLM safety
testing, and Python/FastAPI. Do NOT re-explain their own codebase to them.

## Where things live

```
gemma4_comp/
├── packages/                           <- 17 package surfaces (PEP 420 namespace under duecare.*)
│   ├── duecare-llm-core/                 <- duecare.core.* + duecare.observability.*
│   ├── duecare-llm-models/               <- duecare.models.* (8 adapters with optional extras)
│   ├── duecare-llm-domains/              <- duecare.domains.*
│   ├── duecare-llm-tasks/                <- duecare.tasks.* (9 capability tests)
│   ├── duecare-llm-agents/               <- duecare.agents.* (12-agent swarm)
│   ├── duecare-llm-workflows/            <- duecare.workflows.*
│   ├── duecare-llm-publishing/           <- duecare.publishing.*
│   ├── duecare-llm-chat/                 <- workbench chat UI and Kaggle helper server
│   ├── duecare-llm-server/               <- FastAPI product/server surface
│   ├── duecare-llm-engine/               <- core moderation/evidence pipeline
│   ├── duecare-llm-evidence-db/          <- local evidence store
│   ├── duecare-llm-benchmark/            <- smoke benchmarks and scoring helpers
│   ├── duecare-llm-training/             <- Unsloth SFT/DPO support
│   ├── duecare-llm-research-tools/       <- corpus/search helpers
│   ├── duecare-llm-nl2sql/               <- natural-language SQL guardrail
│   ├── duecare-llm-cli/                  <- operational CLI package
│   └── duecare-llm/                      <- meta package: workflow CLI entry point
│
├── pyproject.toml                      <- uv workspace root
│
├── _reference/                         <- existing assets, NOT public
│   ├── REFERENCE_INDEX.md              <- start here for navigation
│   ├── CLAUDE.md                       <- SOURCE framework's CLAUDE.md (NOT this file)
│   ├── ARCHITECTURE_PLAN.md            <- data model, prompt schema, eval modes
│   ├── README.md                       <- ecosystem overview
│   ├── <sector>_*.md                   <- education/fishing/FB/FTZ/whistleblower summaries
│   ├── reference_publication.txt
│   ├── trafficking_llm_benchmark/      <- 10.3 GB dev benchmark (300K+ LOC)
│   ├── trafficking-llm-benchmark-gitlab/  <- 122 MB, 21K public tests
│   └── framework/                      <- llm-safety-framework-public (copied 2026-04-11)
│
├── _archive/                           <- legacy / superseded files
│   ├── legacy-research-2026-05-09/     <- archived legacy notebooks + skunkworks
│   └── legacy_src/                     <- pre-Duecare flat scaffolds (kept for reference)
│       ├── src/                        <- 627 modules, 29.8K LOC
│       │   ├── research/agents/        <- 12 autonomous agents + coordinator
│       │   ├── scraper/                <- Playwright + stealth stack, 176 seed modules
│       │   ├── prompt_injection/       <- 631 mutators, 55 categories, 44K LOC
│       │   ├── intelligent_attack/     <- 49 classes, 23.6K LOC, embedding/Bayesian/Shapley
│       │   ├── chain_detection/        <- 126 chains, test engine, 5 prompt modes
│       │   ├── generators/             <- 16 domain generators
│       │   ├── cartography/            <- topology mapping, blind spot detection
│       │   ├── dimensional_matrix/     <- 45-dimension scoring
│       │   ├── evaluation/             <- LLM-as-judge, pattern evaluator
│       │   ├── core/                   <- HarnessAgent base, api_specification
│       │   ├── integrations/           <- garak/PyRIT/HarmBench/TextAttack adapters + research APIs
│       │   ├── local_models/           <- model registry, LoRA trainer
│       │   ├── training/               <- safety_evaluator, 4-framework exporter
│       │   ├── spinning/               <- spintax/regex/charpad/LLM rephrase
│       │   ├── swarm/                  <- parallel testing
│       │   └── web/                    <- 18-plugin FastAPI dashboard
│       ├── tests/                      <- 59 files, 7.2K LOC, full Playwright E2E
│       ├── scripts/                    <- 18 orchestration scripts
│       ├── docs/                       <- CLAUDE, ATTACK_TAXONOMY, CHAIN_DETECTION,
│       │                                  PROMPT_INJECTION, DIMENSIONAL_MATRIX, ...
│       ├── pyproject.toml, Makefile, Dockerfile, docker-compose.yml
│       └── .env.template, .pre-commit-config.yaml
├── docs/
│   ├── project_overview.md   <- hackathon strategy, track alignment, timeline
│   ├── architecture.md       <- THIS project's technical design (20 sections)
│   ├── integration_plan.md   <- mapping of framework+benchmark assets -> packages/
│   ├── writeup_draft.md      <- Kaggle writeup draft (<=1,500 words)
│   └── video_script.md       <- 3-minute narration draft
├── src/demo/                 <- FastAPI dashboard + demo app (live)
├── README.md                 <- public-facing project overview for judges
├── LICENSE                   <- MIT (required by the hackathon rules)
├── CLAUDE.md                 <- THIS file
├── requirements.txt
├── copy_reference.py         <- populates _reference/ from the source folder
└── copy_framework.py         <- populates _reference/framework/ from framework source
```

## Archive and context hygiene

The final hackathon project should stay focused on the active submission
surface: `apps/`, `packages/`, `kaggle/` submission folders, `configs/`,
`scripts/`, `docs/`, `deployment/`, `src/demo/`, and `tests/`.

Archived material is intentionally out of the default review scope:

- `_archive/legacy-research-2026-05-09/legacy_notebooks/` contains the
   old 77-notebook research-pipeline mirrors.
- `_archive/legacy-research-2026-05-09/skunkworks/` contains exploratory
   jailbreak / proof-of-concept notebooks.
- `_archive/legacy_src/` contains pre-DueCare scaffolding.

Do **not** read, review, lint, validate, regenerate, or summarize these
archive folders unless the user explicitly asks for historical context,
restore work, provenance checks, or migration work. They are not part of
the active Kaggle submission path. Treat only `01-duecare-exploration-workbench`,
`02-live-demo`, and `A-00-omni-experiment-workbench` under `kaggle/` as active
kernel sources; `kaggle/kernels/*` and other appendix/video folders are archived.

Some older builder scripts may recreate root-level `legacy_notebooks/`
or `skunkworks/` as optional local mirrors. Those root folders are
gitignored convenience artifacts, not active submission sources. Do not
re-add them to git unless Taylor explicitly requests a restore/migration.

## Kaggle publication workflow

Kaggle publishing is manual by default. Do **not** create new Kaggle
notebooks, push kernels, publish datasets/models, or rewrite Kaggle links
automatically unless Taylor explicitly asks for that action.

Kaggle notebook generation is archived. Do **not** create `.ipynb` notebooks
for the judge-facing submission by default. The source of truth for Kaggle
bundles is the folder README plus `kernel.py`; Taylor copies `kernel.py` into
Kaggle manually for showcasing and publication. Any historical `.ipynb` wrapper
belongs under `_archive/kaggle-notebook-previews-2026-05-11/`, not in active
`kaggle/*/` folders.

Builder scripts under `scripts/build_notebook_*.py` are historical research
helpers unless Taylor explicitly asks for a preview rebuild. They must not
write root submission `.ipynb` files.

Every Kaggle bundle that remains in the submission must be runnable from a
clear bootstrap path instead of hidden local state. The first executable cells
or top-of-file setup block should:

1. State required Kaggle settings up front: accelerator, internet, attached
   datasets/model sources, and secrets such as `HF_TOKEN`.
2. Fail fast with a helpful message if the required GPU/secret/dataset is
   missing. If a sample/offline fallback exists, it must be clearly labeled in
   the output and opening markdown so it is never mistaken for live inference.
3. Install DueCare from a reproducible, transparent source. For the current
   rapid Kaggle copy/paste workflow, the active kernels may fall back to
   GitHub source install from `DUECARE_REPO` / `DUECARE_COMMIT_SHA` when
   release wheels are missing. Always print the repo, ref, resolved package
   imports, and DueCare version. For a final frozen submission, prefer a
   commit SHA or release wheel over a moving branch.
4. Validate imports and print the resolved DueCare version/source before any
   model load or demo output.
5. Never require `_reference/`, local `.venv`, root-level legacy mirrors, or
   untracked files to make a public kernel run.

Default agent behavior:

1. Edit source files and kernel bundles locally only.
2. Run validators and dry-runs (public-surface audits, root metadata checks,
   and Kaggle dry-run checks) to prove readiness.
3. Prepare paste-ready kernel text, metadata, and link checklists.
4. Leave the final Kaggle UI steps to Taylor: manual copy/paste into
    Kaggle, manual save/run/publish, then manual link updates after the
    public URLs exist.

Only run real Kaggle push/publish commands after an explicit user request
that says to publish/push/upload. When in doubt, run dry-run/status only.

## Kaggle notebook polish checkpoint (2026-05-11)

Current active Kaggle state is deliberately smaller than the older archived
research suite:

- The former generated/research kernel inventory under `kaggle/kernels/*` is
   archived with its notebook wrappers under
   `_archive/kaggle-notebook-previews-2026-05-11/`. Older 52/74/77-kernel
   notes are historical unless Taylor explicitly asks for restore or migration work.
- The judge-facing submission folders under `kaggle/` are now the active
   three-folder set: `01-duecare-exploration-workbench`, `02-live-demo`, and
   `A-00-omni-experiment-workbench`. Their `kernel.py` and `README.md` files
   are the source of truth; notebook wrappers are archived.
- Appendix folders A-01 through A-24 and `03-duecare-video-pitch` are archived
   for the current push. Do not treat them as active blockers unless Taylor
   asks for restore/migration work.
- A conservative first polish pass has already fixed reproducible bootstrap
   drift, notebook preview cell metadata, visible demo PII placeholders, A-08
   design-token drift, and A-09 displayed-result truncation.
- Older install-policy tests were written for a frozen publication pass.
   Current active kernels prioritize copy/paste Kaggle reliability: attached
   wheels when available, otherwise GitHub source fallback with explicit repo
   and ref logging. If Taylor asks for a freeze, switch defaults to an
   immutable commit SHA.
- If a reviewer or subagent reports `kaggle/01-duecare-harness-chat/kernel.py`,
   treat it as stale context first. As of this checkpoint, that path does not
   exist and is not tracked by git.
- Latest validation after the conservative pass: targeted Kaggle install and
   utility tests passed, active notebook files were archived, root Kaggle
   metadata points to script kernels, and `scripts/validate_public_surface.py`
   reported 0 findings.

Next safe pass for Claude Code: review the shared FastModel runtime, Kernel 01
comparison harness wiring, and A-00 preconfigured pipeline parity. Do not
broaden into archived notebooks, broad redesigns, or Kaggle publish actions
without explicit Taylor approval.

## Project memory

Project memory for Claude Code sessions is at:
`C:\Users\amare\.claude\projects\C--Users-amare-OneDrive-Documents-gemma4-comp\memory\`

Files of note:
- `MEMORY.md` - index
- `user_identity.md` - who Taylor is and how to work with them
- `project_gemma4_hackathon.md` - hackathon scope, concept, timeline
- `feedback_autonomy.md` - "execute, don't ask" - pick sensible defaults

## Conventions

- Python 3.11+ (matches the existing framework)
- Type hints on all functions
- Pydantic v2 for data models
- Unsloth for fine-tuning (Special Tech track)
- llama.cpp (GGUF) and LiteRT for deployment (Special Tech tracks)
- FastAPI for the demo web app (matches existing framework)
- MIT license on all new code
- The `_reference/` folder is `.gitignore`d because it is the author's
  private benchmark harness and publishing it would break data provenance
  guarantees to NGO partners. Only the fine-tuned MODEL weights + the
  benchmark suite that is already public (the `trafficking-llm-benchmark-gitlab`
  21K-test release) should end up in the public Kaggle repo.

## Resolved decisions (2026-04-18)

1. **Unsloth fine-tune**: implemented in 525, 527, 530; Phase 3 curriculum
   plus uncensored 5-grade generator plus full LoRA fine-tune all live.
2. **Gemma model**: E4B is the primary baseline (100) with a dedicated
   E2B like-for-like (102). E2B is the on-device story; E4B is the
   headline quality number.
3. **Deployment target priority**: llama.cpp desktop is the current
   runtime target (600/610 results dashboard, submission walkthrough).
   LiteRT mobile is the next target; the archived deployment-application
   mirror was 670 Private Client-Side Checker.
4. **Video hosting**: public YouTube under Taylor's channel.

## Useful commands

```bash
# ── Local evaluation via Ollama (no Kaggle needed) ──
ollama pull gemma4:e4b                        # download model (~4GB in Q4)
python scripts/run_local_gemma.py --max-prompts 10   # quick test
python scripts/run_local_gemma.py --graded-only      # 204 graded prompts
python scripts/run_local_gemma.py --model gemma4:e2b  # smaller model

# ── Extract prompts from the benchmark ──
python scripts/extract_benchmark_prompts.py   # 74K+ prompts → seed_prompts.jsonl

# ── Build and test ──
python -m pytest packages --collect-only -q   # quick package collection check (675 collected on 2026-05-19)
make test                                     # full package + top-level pytest run; only claim "passed" after it completes
make build                                    # rebuild all 17 workspace wheels
make adversarial                              # adversarial validation + stress test
make cleanroom                                # clean-room install test

# ── Kaggle validation / dry-run only by default ──
python scripts/publish_kaggle.py auth-check
python scripts/publish_kaggle.py --dry-run push-notebooks
python scripts/publish_kaggle.py status-notebooks

# ── Notebook previews are archived; active submission is kernel.py only ──
# Do not create root submission notebooks by default. Use kernel.py and
# folder README as the Kaggle copy/paste source. Historical previews live
# under _archive/kaggle-notebook-previews-2026-05-11/.
```

## Hackathon requirements checklist

- [ ] Kaggle writeup (<=1,500 words) - draft at `docs/writeup_draft.md`
- [ ] Public YouTube video (<=3 minutes) - script at `docs/video_script.md`
- [ ] Public code repo - this repo, minus `_reference/`
- [ ] Live public demo - `src/demo/`, deployment TBD
- [ ] Uses Gemma 4 (E2B or E4B) - yes
- [ ] Bonus: Special Tech Track alignment - Unsloth + (llama.cpp | LiteRT)
