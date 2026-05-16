# Repository cleanup review — 2026-05-10

This review answers the question: which markdown-heavy or duplicate-looking surfaces should stay active, which should be archived, and which should be consolidated later without disrupting the public website, Kaggle submission, or package workflow.

## Inventory snapshot

Active markdown count excluding `.git/`, `.venv/`, `_archive/`, `_reference/`, build outputs, and caches after this cleanup pass: **802** files.

| Area | Markdown count | Cleanup interpretation |
|---|---:|---|
| `packages/` | 554 | Mostly generated folder-per-module docs (`PURPOSE.md`, `STATUS.md`, `TESTS.md`, diagrams). Keep unless the package/module is removed. |
| `docs/` | 148 | Public docs plus current readiness/architecture docs. Curated MkDocs navigation keeps the public path smaller than the raw file count. |
| `.claude/` | 20 | Active agent rules and commands. Keep. |
| `kaggle/` | 16 | Active submission/readme surfaces. Keep; publishing remains manual. |
| `examples/` | 13 | Active examples, now indexed by `examples/README.md`. Keep, but mark planned examples clearly. |
| `apps/`, `deployment/`, `data/`, `release/`, `infra/`, `src/`, `tests/`, root files | remaining | Mixed active docs, reports, and legacy bundles. Review individually before moving. |

## Actions taken

| Action | Rationale |
|---|---|
| Archived `deployment/hf_spaces/` to `_archive/cleanup-2026-05-10/deployment_hf_spaces/`. | It duplicated older Hugging Face Spaces guidance and conflicted with the clearer active root bundles. |
| Archived old handoff prompt docs to `_archive/cleanup-2026-05-10/docs_handoff_prompts/`. | They were single-session planning artifacts and not the current assistant source of truth. |
| Archived `docs/prompts/` to `_archive/cleanup-2026-05-10/docs_prompts_legacy/`. | It was a legacy notebook-prompt ladder with stale publish-oriented instructions; active notebook work now uses builders, validators, and manual Kaggle publishing. |
| Archived stale planning docs to `_archive/cleanup-2026-05-10/docs_stale_planning/`. | They referenced older deployment/publish flows and are superseded by the current readiness and Kaggle guardrail docs. |
| Kept both `hf_space/` and `hf-space/`. | They are not duplicates: `hf_space/` is Harness Chat; `hf-space/` is Live Demo. Renaming either before submission risks breaking deployment assumptions. |
| Added `examples/README.md`. | Consolidates the example folder without moving active examples. |
| Added `docs/launch_packaging_options.md`. | Captures non-Docker launch paths such as `pipx`, offline wheelhouses, EC2 AMIs, and marketplace images without overclaiming availability. |
| Added `docs/kaggle_benchmark_plan.md`. | Captures the Kaggle benchmark path as a manual publication track. |

## Keep active for now

| Surface | Reason |
|---|---|
| `hf_space/` | Active Harness Chat Hugging Face Space bundle. |
| `hf-space/` | Active Live Demo Hugging Face Space bundle. |
| `examples/deployment/` and `examples/embedding/` | Linked from README/docs and useful for developer onboarding. Consolidate via indexes before moving code. |
| `evidence_raw/` | Gitignored raw-evidence intake area. Keep separate from examples; do not add tracked files here unless intentionally force-added after redaction review. |
| `raw_python/` | Gitignored legacy/raw build area referenced by some one-off scripts. Do not publish; review later after notebook builders are stable. |
| `release/duecare_demo_v1/` | Older release bundle. Likely archive candidate later, but it contains sample/demo material and should be reviewed separately. |

## Future archive candidates

Only move these after a link/reference check and a quick stale-claim scan:

- `release/duecare_demo_v1/` if superseded by `duecare-llm-cli` setup and current Kaggle bundles

## Folder policy

- **Examples stay examples:** keep runnable examples under `examples/deployment/` and `examples/embedding/`, with status labels for working vs planned.
- **Raw evidence stays separate:** raw worker chats, IDs, contact details, and private documents must remain in gitignored intake areas until explicitly sanitized/exported by an authorized user.
- **Public/sanitized data lives under `data/` or package data:** use `data/` for reproducible public corpora and package `_data/` folders for lightweight installable samples.
- **Archive instead of delete:** use `_archive/<date-or-purpose>/` with a manifest when moving stale files.