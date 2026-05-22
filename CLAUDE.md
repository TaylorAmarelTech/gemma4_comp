# CLAUDE.md - DueCare project context

> Context for Claude / Claude Code sessions working on this project.
> If you are a new AI assistant picking up this project, read this first.
>
> **This file is a slim index.** Detailed operating rules live under
> `.claude/rules/*.md` and are auto-loaded by Claude Code. The
> 2026-05-22 split moved ~500 lines of inline rules into per-topic
> rule files; this index keeps only the highest-frequency context
> (current operating brief, three overarching goals, rules index,
> project intro, author, project memory).

## Current operating brief (2026-05-22)

- Active submission work is the three-kernel path: `kaggle/01-duecare-exploration-workbench`, `kaggle/02-live-demo`, and `kaggle/A-00-omni-experiment-workbench`. Recording-critical contract: [`.claude/rules/80_active_surface.md`](.claude/rules/80_active_surface.md).
- Optional benchmark work lives in `kaggle/03-universal-llm-benchmark` for arbitrary endpoint comparisons and `kaggle/04-kaggle-community-benchmark` for Kaggle-native Community Benchmark tasks. Neither replaces the three-kernel recording path.
- The public story has six setup lanes in this order: Platform safety, NGO & regulator, Individual worker / mobile, Researcher, Anonymized knowledge sharing, Developer / integration partner.
- The workspace has 17 `duecare-llm*` package directories. The latest verified local collection is 675 package tests collected; do not claim a full pass unless you ran the full suite.
- **Knowledge surface state (verified via `scripts/verify_knowledge_surfaces.py`):** 290 GREP rules (categories A-III) · 215 RAG documents (incl. 6 landmark case-law + 3 national anti-trafficking units) · 34 complaint / narrative templates · 22 review personas · 45 fee-camouflage labels · 31 corridor fee-cap entries · 30 NGO contact bundles · 15 ILO conventions · 74,640 trafficking seed prompts. See [`docs/KNOWLEDGE_SURFACE_VERIFICATION.md`](docs/KNOWLEDGE_SURFACE_VERIFICATION.md).
- Local pip + venv currently broken (OneDrive-sync corruption — `typing_extensions`, `pip._vendor`, `numpy._core` missing across Python 3.10/3.12/3.14 installs). `scripts/verify_knowledge_surfaces.py` works around this with pure stdlib parsing. Boot via Kaggle, which uses each `kernel.py`'s own dependency block.
- Documentation edits should follow `docs/DOCUMENTATION_GUIDE.md`; agent edits should also honor the root `AGENTS.md`.
- Repo-organization edits should also keep `docs/FILE_PURPOSE_GUIDE.md` and the relevant directory index current.
- Keep generated report files out of commits unless Taylor explicitly asks to publish them.

## Three overarching goals (every prompt, every action)

Full text: [`.claude/rules/00_overarching_goals.md`](.claude/rules/00_overarching_goals.md).

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
of them, it gets cut.

## Auto-loaded rules

`.claude/rules/*.md` files are auto-loaded by Claude Code at the project
memory level. Current set:

| # | File | Topic |
|---|---|---|
| 00 | [`00_overarching_goals.md`](.claude/rules/00_overarching_goals.md) | Three rubric goals (Impact / Video / Tech) |
| 10 | [`10_safety_gate.md`](.claude/rules/10_safety_gate.md) | No PII in git / logs / artifacts |
| 20 | [`20_code_style.md`](.claude/rules/20_code_style.md) | Python 3.11+, Pydantic v2, Protocol-based |
| 30 | [`30_test_before_commit.md`](.claude/rules/30_test_before_commit.md) | `duecare test` before PR |
| 40 | [`40_forge_module_contract.md`](.claude/rules/40_forge_module_contract.md) | Folder-per-module pattern |
| 50 | [`50_publish_strategy.md`](.claude/rules/50_publish_strategy.md) | GitHub + multi-package PyPI + Kaggle |
| 60 | [`60_notebook_presentation.md`](.claude/rules/60_notebook_presentation.md) | Kaggle-safe styling, no truncation, shared helpers |
| 70 | [`70_workbench_ui_primitives.md`](.claude/rules/70_workbench_ui_primitives.md) | Activity log + status discoverability + sample artifact + trust boundary |
| 80 | [`80_active_surface.md`](.claude/rules/80_active_surface.md) | Recording-critical kernels + 4-phase arc + independent components + deployment modes + hackathon checklist |
| 81 | [`81_canonical_runtime.md`](.claude/rules/81_canonical_runtime.md) | `Gemma4Runtime.load()` source of truth + A-00 proof path + universal harness abstraction + workbench model-loading UI + multi-harness architecture + naming convention |
| 82 | [`82_project_structure.md`](.claude/rules/82_project_structure.md) | Directory tree + archive hygiene + Python conventions + resolved decisions |
| 83 | [`83_kaggle_workflow.md`](.claude/rules/83_kaggle_workflow.md) | Manual-by-default publishing + polish checkpoint + useful commands |

Additional root guidance:

- [`AGENTS.md`](AGENTS.md) - cross-agent repo orientation and validation commands.
- [`docs/DOCUMENTATION_GUIDE.md`](docs/DOCUMENTATION_GUIDE.md) - canonical public facts and documentation claims policy.

Harness contract docs (load with `@docs/...` when relevant):

- [`docs/harness_pattern.md`](docs/harness_pattern.md) - module contract + 10-step recipe.
- [`docs/harness_ecosystem.md`](docs/harness_ecosystem.md) - vocabulary + registered inventory.
- [`docs/harness_standard_contract.md`](docs/harness_standard_contract.md) - HarnessSpec fields.
- [`docs/MIGRATION_HARNESS_PATTERN.md`](docs/MIGRATION_HARNESS_PATTERN.md) - migration from singular `duecare.chat.harness` to `duecare.chat.harnesses`.

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

## Project memory

Project memory for Claude Code sessions is at:
`C:\Users\amare\.claude\projects\C--Users-amare-OneDrive-Documents-gemma4-comp\memory\`

Files of note:

- `MEMORY.md` - index (current state snapshot at top)
- `project_state_2026_05_22.md` - latest snapshot (knowledge-layer mega expansion)
- `user_identity.md` - who Taylor is and how to work with them
- `project_gemma4_hackathon.md` - hackathon scope, concept, timeline
- `project_harness_architecture.md` - multi-harness architecture summary
- `feedback_autonomy.md` - "execute, don't ask" - pick sensible defaults

## How to use this index

When you need detail on:

- **What active surfaces matter for recording / the rubric:** see [`80_active_surface.md`](.claude/rules/80_active_surface.md).
- **How Gemma 4 loads / harness contract / workbench UI:** see [`81_canonical_runtime.md`](.claude/rules/81_canonical_runtime.md).
- **Repo layout / archive hygiene / Python conventions:** see [`82_project_structure.md`](.claude/rules/82_project_structure.md).
- **How to publish to Kaggle / useful CLI commands:** see [`83_kaggle_workflow.md`](.claude/rules/83_kaggle_workflow.md).
- **Knowledge-layer current counts + smoke verification:** see [`docs/KNOWLEDGE_SURFACE_VERIFICATION.md`](docs/KNOWLEDGE_SURFACE_VERIFICATION.md).

All rules files are auto-loaded so you do not need to manually open them
during a session; this index is for human + reviewer navigation.
