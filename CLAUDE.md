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

## Current operating brief (2026-05-24)

- Active submission work is the three-kernel path: `kaggle/01-duecare-exploration-workbench`, `kaggle/02-live-demo`, and `kaggle/A-00-omni-experiment-workbench`. Recording-critical contract: [`.claude/rules/80_active_surface.md`](.claude/rules/80_active_surface.md).
- Optional benchmark work lives in `kaggle/03-universal-llm-benchmark` for arbitrary endpoint comparisons and `kaggle/04-kaggle-community-benchmark` for Kaggle-native Community Benchmark tasks. Neither replaces the three-kernel recording path.
- The public story has six setup lanes in this order: Platform safety, NGO & regulator, Individual worker / mobile, Researcher, Anonymized knowledge sharing, Developer / integration partner.
- The workspace has 17 `duecare-llm*` package directories. As of 2026-05-28 the full suite is **1,493 tests** (run via `pwsh scripts/recover_test_env.ps1 -Full`): **1,490 pass, 3 skip, 0 fail — fully green**. The 15 pre-existing drift failures cataloged in [`docs/handoff_2026_05_27.md`](docs/handoff_2026_05_27.md) (docs, kernel-inventory, ui-audit, community-benchmark, and publish-orchestrator reconciliation) were all resolved 2026-05-27→28, along with the earlier 2 forge e2e and A-00 source-audit fixes. The 3 skips are conditional config-not-populated guards. Do not claim a full pass unless you ran the full suite.
- **Safe-text layer (2026-05-24):** `packages/duecare-llm-chat/src/duecare/chat/harnesses/_safe_text.py` is the single chokepoint every fact / share / search / template output flows through. Three concentric layers — scrub (kernel paths / RUN_IDs / synthetic case folder names), standardize (canonical 47-field envelope shape + 16 ILO indicators + 9 stages + XX-YY corridors), and the iterative polish endpoint `POST /api/knowledge/polish-envelope` (two Gemma 4 passes: critique then rewrite). UI: "Polish further (Gemma 4)" button in knowledge.html and search.html draft cards; both polish panels use the shared `window.dcDiff` inline word-diff renderer; knowledge.html also has a persisted sequential auto-polish queue for new draft batches; process.html typed edges can draft/polish/promote knowledge facts via `POST /api/knowledge/from-edge`; templates.html has `/static/samples/template_bundle_sample.json` with Download/Use sample buttons, `POST /api/templates/dry-run-fill` for pre-Generate field-source preview, and `POST /api/templates/fill-batch` behind "Fill all relevant" for batch drafting relevant templates from one bundle excerpt. Full reference: [`docs/safe_text_layer.md`](docs/safe_text_layer.md). Follow-up improvements ready to dispatch: [`docs/codex_followup_goals.md`](docs/codex_followup_goals.md).
- **Bulk File Review graph gap (2026-05-24):** the visible `gemma_case_brief` phase is bundle-level synthesis. Deterministic parsing already creates row/page/chunk/folder-grounded typed edges, and bounded Gemma edge/media passes can add model edges, but the next architectural target is explicit hierarchical Gemma node/edge passes across folder, document, page, chunk, media, person, case, and rollup levels. Track this as [`docs/codex/goal_11_hierarchical_gemma_graph/handoff.md`](docs/codex/goal_11_hierarchical_gemma_graph/handoff.md).
- **Knowledge surface state (verified via `scripts/verify_knowledge_surfaces.py`):** 451 GREP rules (categories A-NNNN; MMMM 2026-06-08: sham-status / misclassification citing ILO C095/R198; NNNN 2026-06-10: 24 digital-recruitment / crypto+e-wallet fee-rail / Gulf free-visa / student-visa-labour / corridor-depth rules citing ILO C181 Art.7 + Fair Recruitment 2016 + ICRMW Art.21) · 859 RAG documents (trafficking corpus; +13 migrant-worker conventions ILO C097/C143/ICRMW + IRIS + BD/ID/LK/IN origin-state laws + Kuwait DW law + US TVPA + AU/CA supply-chain acts + CoE Warsaw) plus a SEPARATE 610-doc multidomain corpus (51 integrity verticals, opt-in BM25 at `GET /api/multidomain/rag`, never commingled) · 652 example/showcase prompts (`_examples.json`, 8 audience buckets) · 36 complaint / narrative templates · 37 review personas · 57 fee-camouflage labels · 38 corridor fee-cap entries · 36 NGO contact bundles · 16 ILO conventions · 74,640 trafficking seed prompts. See [`docs/KNOWLEDGE_SURFACE_VERIFICATION.md`](docs/KNOWLEDGE_SURFACE_VERIFICATION.md).
- **Session 2026-06-09 (holistic review + hardening):** Standardized the KnowledgeObject v1.0 envelope (`packages/duecare-llm-chat/src/duecare/chat/knowledge_taxonomy.py` — validator with binding per-type required-content-keys, `content_sha256` integrity hash, `DUECARE_NODE_ID` provenance, generated `static/envelope_schema.json` served by kernel + hub). Federation peer registry (`federation.py`, `DUECARE_PEERS`, `GET /api/network/peers`) is now the single outbound allowlist — closed an unvalidated `target_url` SSRF hole in `/api/knowledge/sync`. Harness-lift report has real paired statistics (`scripts/lift_stats.py` + `scripts/build_lift_report.py --all` → committed `docs/research/harness_lift_report.md`, regeneratable HTML, and `static/lift_evidence.json` surfaced on the compare page + render `/evaluation`): gemma4:31b **+1.73/10** mean paired lift, 95% CI [+1.57,+1.89], 73.3% win rate, Cohen's d 0.69, judged by gpt-oss:120b over 911 prompts. Safety fix: the extraction training-log scrub was being DISABLED by the request anonymize flag (raw text → fine-tune JSONL) — now always-on and using the canonical detector patterns. Shared `_envelope_card.js` renderer + `.wb-next-steps` end-of-page block. Graph review: `docs/research/graph_stack_review_2026_06_09.md`. Full detail in this session's commits (`b3bda5c2`..HEAD).
- The system Python is corrupted by OneDrive sync **down to the stdlib** (`typing_extensions`, the compiled `pydantic_core.pyd`, `pydantic.main`, and `html.entities` have all been stripped; `pip` broken). **To run tests, use `pwsh scripts/recover_test_env.ps1 -Run` (or `-Full`)** — it builds a clean uv-managed CPython venv outside the OneDrive tree (see [`docs/local_test_env.md`](docs/local_test_env.md)). For quick checks without a venv, `scripts/verify_knowledge_surfaces.py` and `python -c "import runpy; runpy.run_path('<path>.py')"` still work. GPU/model runs still boot via Kaggle.
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
- [`docs/safe_text_layer.md`](docs/safe_text_layer.md) - shared scrub / standardize / iterative-polish chokepoint (2026-05-24). Canonical fact-envelope shape, ILO vocab, polish endpoint, provenance flags.
- [`docs/codex_followup_goals.md`](docs/codex_followup_goals.md) - ten copy-paste improvement prompts sized for a single Codex session each.

## What this project is

A submission for the **Gemma 4 Good Hackathon** on Kaggle (2026-04-02 through
2026-05-18, $200K prize pool across Main/Impact/Special Technology tracks).
**Submission window closed 2026-05-18.** Post-deadline work continues on the
same kernels for polish, NGO-partner-ready integration, and judge-facing UX.

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
- **Fact-shape normalization / noise scrubbing / iterative Gemma polish:** see [`docs/safe_text_layer.md`](docs/safe_text_layer.md). Pickable next-up improvements: [`docs/codex_followup_goals.md`](docs/codex_followup_goals.md).
- **Knowledge-layer current counts + smoke verification:** see [`docs/KNOWLEDGE_SURFACE_VERIFICATION.md`](docs/KNOWLEDGE_SURFACE_VERIFICATION.md).

All rules files are auto-loaded so you do not need to manually open them
during a session; this index is for human + reviewer navigation.
