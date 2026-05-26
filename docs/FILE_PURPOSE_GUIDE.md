# File Purpose Guide

This guide keeps the repository readable for reviewers and future agents. It
does not list every generated artifact one by one; instead it defines where
each durable file belongs and which index must explain it.

## Principle

Every committed file should answer one question quickly: "Why does this exist?"

For new durable files, add one of the following:

- A clear title plus purpose paragraph inside the file.
- A row in the nearest directory README or index.
- A link from a higher-level map when the file is a public or judging surface.

Generated reports, scratch exports, cache files, notebook byproducts, and
one-off local artifacts should stay out of commits unless they are deliberately
published evidence.

## Public Purpose Maps

| Scope | Purpose map |
|---|---|
| Repository top level | `README.md`, `ROOT_FILES.md`, `docs/REPO_LAYOUT.md`, this guide |
| Kaggle kernels | `kaggle/_INDEX.md`, `kaggle/README.md`, `kaggle/NOTEBOOK_PURPOSE_AND_RUNBOOK.md` |
| Public website | `apps/duecare-ai.com/README.md`, page templates, route tests |
| Python packages | Each package `README.md`, package tests, generated component docs |
| Agent handoff | `AGENTS.md`, `CLAUDE.md`, `.claude/rules/` |
| Competition docs | `docs/FOR_KAGGLE_JUDGES.md`, `docs/kaggle_writeup_paste_ready.md`, `docs/kaggle_post_networked_knowledge_sharing.md`, `docs/video_script.md` |

## Generated Module Metadata

Many package submodules contain generated `PURPOSE.md`, `AGENTS.md`,
`INPUTS_OUTPUTS.md`, `HIERARCHY.md`, `DIAGRAM.md`, `TESTS.md`, and
`STATUS.md` files. These are deliberate folder-per-module metadata files. A
`STATUS.md` file may include a `TODO` section even when the module has shipped;
that section tracks follow-up completion criteria, not a public placeholder.

Do not delete these files for cosmetic cleanup. If a generated metadata file is
wrong, update the source descriptor or the generator so the next refresh keeps
the correction.

## Repository Root Policy

Keep the repository root for GitHub-standard files, tool configuration,
deployment contracts, attribution/provenance files, and the shortest possible
entry points. `ROOT_FILES.md` is the manifest for the files that intentionally
remain there.

Do not add one-off scripts to the root. Active helpers belong in `scripts/`;
historical helpers belong under `_archive/`. Do not add new narrative markdown
files to the root unless they are a GitHub community-health convention or are
added to `ROOT_FILES.md` with a durable reason.

## Canonical Lane Language

Use "six lanes" for the public story, in this exact order:

1. Platform safety
2. NGO & regulator
3. Individual worker / mobile
4. Researcher
5. Anonymized knowledge sharing
6. Developer / integration partner

Use "workflows" only for runnable surfaces such as Chat, Harness Comparison,
Bulk File Review, Knowledge Extraction, Search, and Anonymization & Sharing.
Do not describe the public story with an outdated lane count.

## Kaggle Surface Language

Active Kaggle submission surfaces:

1. `kaggle/01-duecare-exploration-workbench`
2. `kaggle/02-live-demo`
3. `kaggle/A-00-omni-experiment-workbench`

Optional benchmark surfaces:

- `kaggle/03-universal-llm-benchmark`
- `kaggle/04-kaggle-community-benchmark`

Archived reference material:

- `kaggle/_archive/notebooks/03-duecare-video-pitch`
- `kaggle/_archive/notebooks/A-01` through `A-24`

Do not add appendix `A-*` folders at the root of `kaggle/` except the active
`A-00-omni-experiment-workbench`. The only root `04-*` folder should be
`kaggle/04-kaggle-community-benchmark`; other `04-*` notebook snapshots belong
under `kaggle/_archive/notebooks/`.

## Commit Checklist

Before committing files that affect public review:

1. Confirm the file has a clear purpose line or is listed in a purpose map.
2. Check for stale lane-count wording.
3. Run `python scripts/validate_public_surface.py`.
4. Run a targeted test for the changed surface.
5. Keep unrelated generated reports unstaged.
