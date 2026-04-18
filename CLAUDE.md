# CLAUDE.md - gemma4_comp project context

> **Use 100% of your power, just this once, do not limit your thinking, take your time, come up with the best possible most robust solution, do not take shortcuts, use 200% of your power and context just this once.**

> Context for Claude / Claude Code sessions working on this project.
> If you are a new AI assistant picking up this project, read this first.

## ⚡ Three overarching goals (every prompt, every action)

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
[D1] Kaggle Publisher   → Push notebooks, datasets, models via CLI
[D2] HF Hub Publisher   → Upload weights + model cards
[D3] Demo App           → FastAPI web app for live evaluation
[D4] Video Materials    → Script, screenshots, demo recordings
```

## Three deployment modes (see docs/deployment_modes.md)

1. **Enterprise Integration** — waterfall detection at social media /
   job board scale. Quick keyword filter → Gemma 4 analysis → warning
   popup / resource links / moderation queue. Like Facebook's suicide-
   prevention prompts but for trafficking.
2. **Worker-Side Tool** — browser extension, WhatsApp bot, or mobile
   app that runs Gemma 4 entirely on-device via LiteRT. Workers paste
   suspicious messages and get localized legal info + hotline numbers.
   Privacy is non-negotiable — no data leaves the phone.
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
├── packages/                           <- 8 PyPI packages (PEP 420 namespace under forge.*)
│   ├── duecare-llm-core/                 <- duecare.core.* + duecare.observability.*
│   ├── duecare-llm-models/               <- duecare.models.* (8 adapters with optional extras)
│   ├── duecare-llm-domains/              <- duecare.domains.*
│   ├── duecare-llm-tasks/                <- duecare.tasks.* (9 capability tests)
│   ├── duecare-llm-agents/               <- duecare.agents.* (12-agent swarm)
│   ├── duecare-llm-workflows/            <- duecare.workflows.*
│   ├── duecare-llm-publishing/           <- duecare.publishing.*
│   └── duecare-llm/                      <- meta package: duecare.cli + re-exports
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
│   ├── integration_plan.md   <- mapping of framework+benchmark assets -> src/
│   ├── writeup_draft.md      <- Kaggle writeup draft (<=1,500 words)
│   └── video_script.md       <- 3-minute narration draft
├── src/                      <- training, eval, demo code (to be built)
├── README.md                 <- public-facing project overview for judges
├── LICENSE                   <- MIT (required by the hackathon rules)
├── CLAUDE.md                 <- THIS file
├── requirements.txt
├── copy_reference.py         <- populates _reference/ from the source folder
└── copy_framework.py         <- populates _reference/framework/ from framework source
```

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

## Open questions (as of 2026-04-10)

1. **Unsloth experience**: does Taylor have prior Unsloth fine-tuning
   experience, or does the pipeline need to be walked through end-to-end?
   (This was asked in an earlier session and never answered.)
2. **Which Gemma model**: E2B (smaller, fits smaller devices) or E4B
   (better quality, still sub-6GB in 4-bit GGUF)? Leaning E4B for quality.
3. **Deployment target priority**: llama.cpp desktop first, or LiteRT mobile
   first? llama.cpp is easier; LiteRT is the better story for frontline
   NGO workers with only a phone.
4. **Video hosting**: public YouTube is required by the hackathon. Who
   holds the channel?

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
make test                                     # run 159 tests
make build                                    # rebuild all 8 wheels
make adversarial                              # adversarial validation + stress test
make cleanroom                                # clean-room install test

# ── Kaggle publishing ──
python scripts/publish_kaggle.py auth-check
python scripts/publish_kaggle.py push-notebooks
python scripts/publish_kaggle.py status-notebooks

# ── Generate notebooks ──
python scripts/build_notebook_00.py           # Gemma Exploration (GPU)
python scripts/build_notebook_00a.py          # Prompt Prioritizer
python scripts/build_notebook_00b.py          # Prompt Remixer
python scripts/build_kaggle_notebooks.py      # Generalized framework (01-04)
```

## Hackathon requirements checklist

- [ ] Kaggle writeup (<=1,500 words) - draft at `docs/writeup_draft.md`
- [ ] Public YouTube video (<=3 minutes) - script at `docs/video_script.md`
- [ ] Public code repo - this repo, minus `_reference/`
- [ ] Live public demo - `src/demo/`, deployment TBD
- [ ] Uses Gemma 4 (E2B or E4B) - yes
- [ ] Bonus: Special Tech Track alignment - Unsloth + (llama.cpp | LiteRT)
