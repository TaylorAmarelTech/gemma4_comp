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
| Public website | `apps/duecare-ai.com/README.md`, `/project-status`, page templates, route and static-export tests |
| Python packages | Each package `README.md`, package tests, generated component docs |
| Agent handoff | `AGENTS.md`, `CLAUDE.md`, `PROJECT_BIBLE.md`, `Plans.md`, `.claude/rules/` |
| Maintainer succession | `docs/MAINTAINER_HANDOFF.md`, `docs/PROJECT_TRANSITION_PLAN.md` |
| Competition docs | `docs/FOR_KAGGLE_JUDGES.md`, `docs/kaggle_writeup_paste_ready.md`, `docs/kaggle_post_networked_knowledge_sharing.md`, `docs/video_script.md` |
| Publication and peer review | `docs/PUBLICATION_READINESS.md`, `docs/FOR_PEER_REVIEW.md`, `docs/reproducibility.md` |

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

Durable training helpers in `scripts/` must be discoverable from
`docs/training_and_finetuning.md`. For example,
`scripts/validate_publication_readiness.py` is the model-free release wrapper:
its core scope composes the portable public, claim, Kaggle, and collection
gates; its handoff scope composes succession and live-pickup checks; and its
separate training scope preserves an honest red result when strict dataset or
provenance checks are not yet clean. `scripts/validate_maintainer_handoff.py`
checks the two current succession documents, their discovery/local links, and
privacy-safe content without calling a model or network service.
`scripts/ollama_adversarial_flywheel.py` is the local Ollama candidate producer:
it may generate SFT/DPO candidates and quarantine metadata, but its manifest
must remain candidate-only until the normal training and publication gates pass.
`scripts/build_kaggle_proof_training_bundle.py` is the deterministic proof
bundle producer for the public Kaggle preview dataset; it emits synthetic,
visible-rationale SFT/preference rows plus held-out splits for the same release
gate.
`scripts/build_multiperspective_training_bundle.py` is the larger deterministic
case-graph producer. It exposes shared dated synthetic records through single,
handoff, and multi-actor views across perspectives, journey stages, temporal
lenses, evidence states, and jurisdiction topologies. It holds out complete
mechanism families, emits an executable quality audit, and requires a separate
manifest-bound publication approval before the normal release gate can run.
`scripts/build_kaggle_interim_collection.py` reverifies the approved proof
release and builds two exact-row Kaggle dataset views plus CPU integrity,
training-plan, and four-arm-evaluation notebooks under gitignored `reports/`.
It does not approve new rows, publish the larger candidate, enable GPU training
by default, or represent visible rationales as hidden chain-of-thought.

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

Shared dataset surfaces are not additional kernels. In particular,
[`kaggle/shared-datasets/training-data`](../kaggle/shared-datasets/training-data/)
is a documentation-only template for a future advanced SFT/preference release.
It must not contain training rows or an active `dataset-metadata.json` until a
clean manifest-bound release has passed provenance, licensing, privacy,
lineage, held-out, and quality gates.

The published proof dataset
[`taylorsamarel/duecare-proof-finetuning-data`](https://www.kaggle.com/datasets/taylorsamarel/duecare-proof-finetuning-data)
is separate from that template. It is a preview artifact generated from
`scripts/build_kaggle_proof_training_bundle.py`, not the full advanced corpus.
Its public SFT and preference views and three completed CPU companion notebooks
are listed in `kaggle/_INDEX.md`; they are auxiliary proof artifacts and do not
change the three-kernel active submission count.

Archived reference material:

- `kaggle/_archive/notebooks/03-duecare-video-pitch`
- `kaggle/_archive/notebooks/A-01` through `A-24`
- `kaggle/_archive/notebooks/A-30-cot-gpu-training`

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
