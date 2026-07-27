# DueCare Project Status

Current as of 2026-07-26.

## Active Submission Scope

The active Kaggle path is exactly three script-kernel folders:

| Kernel | Role |
|---|---|
| `kaggle/01-duecare-exploration-workbench/` | Broad interactive workbench for chat, harness comparison, extraction, search controls, knowledge packs, traces, and activity logs. |
| `kaggle/02-live-demo/` | Focused live demo and video narrative path. |
| `kaggle/A-00-omni-experiment-workbench/` | Quantitative proof path: baseline vs harnessed arms, synthetic data, fine-tune, judging, and report artifacts. |

The public A-00 Kaggle page attaches
`taylorsamarel/duecare-proof-finetuning-data`. That dataset is a guarded
preview, not the full advanced corpus, and Kaggle reports it ready. The Kaggle
execution still needs a terminal status and artifact review before it is cited
as a completed proof run, and no production adapter is published.

The interim training collection is public: the SFT and preference dataset views
both report ready, and the integrity, CPU training-plan, and four-arm evaluation
notebooks all completed on 2026-07-15. These are exact-row companions to the
small approved proof release. The completed training starter emitted a plan but
did not execute GPU training, so this does not close the adapter or model-lift
work.

The retired A-series notebook ladder other than active A-00, task-notebook
snapshots, and older checklist/status docs are archived under
`docs/_archive/2026-05-16-legacy-notebook-era/` or
`kaggle/_archive/notebooks/`. Root `kaggle/` should not contain appendix
`A-*` folders other than `A-00-omni-experiment-workbench`, and the only root `04-*` folder should be
`04-kaggle-community-benchmark`.

## Current Technical Posture

- Live Git differs from the declared release target: root `AGENTS.md` names
  `master`, while the 2026-07-26 workspace is on
  `codex/full-flywheel-training-20260714` with mixed uncommitted work. This is a
  P0 integration/release task, not permission to reset or discard the tree.
- The repository has a single model-free publication entry point:
  [`PUBLICATION_READINESS.md`](PUBLICATION_READINESS.md) and
  `python scripts/validate_publication_readiness.py --scope core`. All eight
  core gates passed in the current workspace on 2026-07-26; rerun them on the
  exact release commit.
- Maintainer succession is now explicit: [`MAINTAINER_HANDOFF.md`](MAINTAINER_HANDOFF.md)
  is the operational pickup, and
  [`PROJECT_TRANSITION_PLAN.md`](PROJECT_TRANSITION_PLAN.md) schedules the
  2026-07-26 through 2026-08-25 closeout. The separate `--scope handoff` gate is
  read-only and keeps both documents linked to live pickup evidence.
- Public deployment ownership is reconciled: `duecare-ai.com` deploys from
  `apps/duecare-ai.com` on Render; GitHub Pages deploys MkDocs through
  `docs-deploy.yml`; the website static exporter remains an artifact workflow
  and cannot overwrite Pages. The website exposes `/project-status` as the
  public continuity entry point.
- New local/hosted Ollama work is deferred. The rich harness supports a
  non-mutating `--plan` and a startup ceiling through
  `--max-planned-model-calls` / `DUECARE_MAX_PLANNED_MODEL_CALLS`.
- The strict training-data audit is not clean: five dense generic-corridor
  typologies produced 25 metadata-only curation tasks and a 75-row minimum
  expansion target. Existing published learning artifacts remain bounded by
  their original manifests; this blocks a new training claim, not review of
  the core repository.
- Local Gemma inference is standardized through `Gemma4Runtime.load()`.
- Active A-00 uses the same offline default harness as the Kernel 01 comparison path:
  Persona + GREP + RAG/context + deterministic tools, with internet/import off.
- Active A-00 can run local Gemma judging by default and optional external judge paths
  when credentials are present.
- Active A-00 training supports checkpoint/resume, adapter save/load, and final report
  export.
- The harness system is documented as an ecosystem rather than a single
  monolithic harness.

## Current Docs To Trust

- [`MAINTAINER_HANDOFF.md`](MAINTAINER_HANDOFF.md) - fresh-shell operations,
  system boundaries, access transfer, recovery, and acceptance.
- [`PROJECT_TRANSITION_PLAN.md`](PROJECT_TRANSITION_PLAN.md) - dated 30-day
  closeout, successor rehearsal, release decision, and maintenance fallback.
- [`FOR_PEER_REVIEW.md`](FOR_PEER_REVIEW.md) - reviewer verification path.
- [`PUBLICATION_READINESS.md`](PUBLICATION_READINESS.md) - offline release gate,
  Ollama-credit plan, dataset roadmap, and additional source candidates.
- [`USER_TODO.md`](USER_TODO.md) - manual actions before submission.
- [`readiness_dashboard.md`](readiness_dashboard.md) - current status snapshot.
- [`two_week_submission_plan.md`](two_week_submission_plan.md) - final execution
  plan.
- [`current_kaggle_notebook_state.md`](current_kaggle_notebook_state.md) -
  active versus archived Kaggle inventory.
- [`harness_ecosystem.md`](harness_ecosystem.md),
  [`harness_pattern.md`](harness_pattern.md), and
  [`harness_standard_contract.md`](harness_standard_contract.md) - harness
  contract and inventory.
- [`model_loading_trace.md`](model_loading_trace.md) - Gemma 4 runtime contract.

## Remaining Work

1. Complete the 30-day access, recovery, release/no-release, successor rehearsal,
   and final acceptance actions in the transition plan.
2. Keep the three active Kaggle source surfaces runnable; capture the two
   recording surfaces only when a new recording is needed.
3. Curate and adjudicate the 75-row corridor expansion before making a new
   fine-tuning or adapter-improvement claim.
4. When model quota is intentionally reopened, freeze and plan a small run,
   set a finite allowance and output cap, and preserve checkpoint/resume state.
5. Attach exact report, activity, prompt/response, training-metadata, chart,
   and evidence artifacts to any new claim.
6. Keep A-00 as the active optional proof path. A-30 and the other appendix
   notebooks remain archived under `kaggle/_archive/notebooks/`.

## Verification

Use the focused commands in [`FOR_PEER_REVIEW.md`](FOR_PEER_REVIEW.md). The docs
contract tests intentionally fail if current entry docs drift back toward the
retired appendix-ladder framing.

Latest offline working-tree receipt on 2026-07-26:

- publication handoff: 2/2 gates passed, including 16/16 succession-document
  checks and 65/65 live pickup checks;
- publication core: 8/8 gates passed;
- combined `packages tests` regression: 4,601 passed and 4 skipped before the
  final integration; the subsequent 43-test package run passes with pandas
  `RuntimeWarning` promoted to an error;
- normal MkDocs build: passed; both succession pages emitted zero diagnostics;
  strict MkDocs remains red on 84 classified legacy warnings;
- training readiness: strict quality and provenance failed as documented,
  while the 25-task corridor plan passed its privacy/safety validation;
- no Ollama or hosted-model call was made during this polish/validation pass.
