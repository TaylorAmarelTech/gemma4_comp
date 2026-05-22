# Project structure + archive hygiene + conventions

> Auto-loaded by Claude Code at the project memory level. Extracted
> from CLAUDE.md so the per-rule files stay scoped.

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
│       ├── tests/                      <- 59 files, 7.2K LOC, full Playwright E2E
│       ├── scripts/                    <- 18 orchestration scripts
│       ├── docs/                       <- CLAUDE, ATTACK_TAXONOMY, CHAIN_DETECTION, ...
│       ├── pyproject.toml, Makefile, Dockerfile, docker-compose.yml
│       └── .env.template, .pre-commit-config.yaml
├── docs/
│   ├── project_overview.md   <- hackathon strategy, track alignment, timeline
│   ├── architecture.md       <- THIS project's technical design (20 sections)
│   ├── integration_plan.md   <- mapping of framework+benchmark assets -> packages/
│   ├── writeup_draft.md      <- Kaggle writeup draft (<=1,500 words)
│   ├── video_script.md       <- 3-minute narration draft
│   └── KNOWLEDGE_SURFACE_VERIFICATION.md  <- current counts + smoke test report
├── src/demo/                 <- FastAPI dashboard + demo app (live)
├── README.md                 <- public-facing project overview for judges
├── ROOT_FILES.md             <- manifest for root-level files that intentionally remain
├── LICENSE                   <- MIT (required by the hackathon rules)
├── CLAUDE.md                 <- THIS file (slim index post-2026-05-22 split)
└── requirements.txt
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
